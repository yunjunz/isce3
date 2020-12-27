"""
Suite of functions to prepare
HDF5 for GSLC, GCOV, GUNW, RIFG, and RUNW
"""

import os
import h5py
import numpy as np

from osgeo import osr

import journal
from pybind_nisar.h5 import cp_h5_meta_data
from pybind_nisar.products.readers import SLC


def run(cfg: dict) -> dict:
    '''
    Copy metadata from src hdf5 and prepare datasets
    Returns dict of output path(s); used for InSAR workflow
    '''
    info_channel = journal.info("h5_prep.run")
    info_channel.log('preparing HDF5')

    output_path = cfg['ProductPathGroup']['SASOutputFile']
    scratch = cfg['ProductPathGroup']['ScratchPath']
    product_type = cfg['PrimaryExecutable']['ProductType']

    # dict keying product type with list with possible product type(s)
    insar_products = ['RIFG', 'RUNW', 'GUNW', 'POLAR']
    product_dict = {'POLAR':insar_products[:-1],
                    'GUNW':insar_products[:-1],
                    'RUNW':insar_products[:-2],
                    'RIFG':[insar_products[0]],
                    'GCOV':['GCOV'],
                    'GSLC':['GSLC']}

    # dict keying product type to dict of product type key(s) to output(s)
    # following lambda creates subproduct specific output path
    insar_path = lambda out_path, product :\
            os.path.join(os.path.dirname(out_path), product+'_'+os.path.basename(out_path))
    h5_paths = {'POLAR':dict(zip(insar_products[:-1],
                                 [insar_path(output_path, product) for product in insar_products[:-1]])),
                'GUNW':{'RIFG':f'{scratch}/RIFG.h5', 'RUNW':f'{scratch}/RUNW.h5', 'GUNW':output_path},
                'RUNW':{'RIFG':f'{scratch}/RIFG.h5', 'RUNW':output_path},
                'RIFG':{'RIFG':output_path},
                'GCOV':{'GCOV':output_path},
                'GSLC':{'GSLC':output_path}}


    for sub_prod_type in product_dict[product_type]:
        out_path = h5_paths[product_type][sub_prod_type]
        cp_geocode_meta(cfg, out_path, sub_prod_type)
        prep_ds(cfg, out_path, sub_prod_type)

    info_channel.log('successfully prepared HDF5')

    return h5_paths[product_type]

def cp_geocode_meta(cfg, output_hdf5, dst):
    '''
    Copy shared data from source HDF5 to GSLC, GCOV, INSAR
    HDF5 destinations
    Parameters:
    -----------
    cfg : dict
        Run configuration
    dst : str or list
        Name of destination node where data is to be copied
    '''

    # Check if InSAR
    is_insar = dst in ['GUNW', 'RUNW', 'RIFG']

    # unpack info
    input_hdf5 = cfg['InputFileGroup']['InputFilePath']
    freq_pols = cfg['processing']['input_subset']['list_of_frequencies']

    if is_insar:
        secondary_hdf5 = cfg['InputFileGroup']['SecondaryFilePath']

    # Remove existing HDF5 and start from scratch
    try:
        os.remove(output_hdf5)
    except FileNotFoundError:
        pass

    # Open reference slc
    ref_slc = SLC(hdf5file=input_hdf5)

    # prelim setup
    common_parent_path = 'science/LSAR'
    src_meta_path = ref_slc.MetadataPath
    dst_meta_path = f'{common_parent_path}/{dst}/metadata'

    with h5py.File(input_hdf5, 'r', libver='latest', swmr=True) as src_h5, \
            h5py.File(output_hdf5, 'w', libver='latest', swmr=True) as dst_h5:

        # Copy of identification
        identification_excludes = 'productType'
        if is_insar:
            identification_excludes = ['productType', 'listOfFrequencies']
        cp_h5_meta_data(src_h5, dst_h5, f'{common_parent_path}/identification',
                        excludes=identification_excludes)

        # Flag isGeocoded
        ident = dst_h5[f'{common_parent_path}/identification']
        is_geocoded = dst in ['GCOV', 'GSLC', 'GUNW']
        dset = ident.create_dataset('isGeocoded', data=np.string_(str(is_geocoded)))
        desc = "Flag to indicate radar geometry or geocoded product"
        dset.attrs["description"] = np.string_(desc)

        # Assign productType
        ident['productType'] = np.string_(dst)

        # copy orbit information group
        cp_h5_meta_data(src_h5, dst_h5, f'{src_meta_path}/orbit',
                        f'{dst_meta_path}/orbit')

        # copy attitude information group
        if is_geocoded:
            cp_h5_meta_data(src_h5, dst_h5, f'{src_meta_path}/attitude',
                            f'{dst_meta_path}/attitude')
            cp_h5_meta_data(src_h5, dst_h5,
                            f'{src_meta_path}/geolocationGrid',
                            f'{dst_meta_path}/radarGrid',
                            renames={'coordinateX': 'xCoordinates',
                                     'coordinateY': 'yCoordinates',
                                     'zeroDopplerTime': 'zeroDopplerAzimuthTime'})
        else:
            # RUNW and RIFG have no attitude group and have geolocation grid
            cp_h5_meta_data(src_h5, dst_h5,
                            f'{src_meta_path}/geolocationGrid',
                            f'{dst_meta_path}/geolocationGrid')

        # copy processingInformation/algorithms group (common across products)
        cp_h5_meta_data(src_h5, dst_h5,
                        f'{src_meta_path}/processingInformation/algorithms',
                        f'{dst_meta_path}/processingInformation/algorithms')

        # copy processingInformation/inputs group
        exclude_args = ['l0bGranules', 'demFiles']
        if not is_geocoded:
            exclude_args = ['attitudeFiles', 'auxcalFiles',
                            'l0bGranules', 'orbitFiles']

        cp_h5_meta_data(src_h5, dst_h5,
                        f'{src_meta_path}/processingInformation/inputs',
                        f'{dst_meta_path}/processingInformation/inputs',
                        excludes=exclude_args)

        # Create l1SlcGranules
        inputs = [input_hdf5]
        if is_insar:
            inputs.append(secondary_hdf5)
        input_grp = dst_h5[os.path.join(dst_meta_path, 'processingInformation/inputs')]
        dset = input_grp.create_dataset("l1SlcGranules", data=np.string_(inputs))
        desc = "List of input L1 RSLC products used"
        dset.attrs["description"] = np.string_(desc)

        # Copy processingInformation/parameters
        if dst == 'GUNW':
            exclude_args = ['frequencyA', 'frequencyB', 'azimuthChirpWeighting',
                            'effectiveVelocity', 'rangeChirpWeighting', 'slantRange', 'zeroDopplerTime']
        elif dst in ['RUNW', 'RIFG']:
            exclude_args = ['frequencyA', 'frequencyB',
                            'azimuthChirpWeighting',
                            'effectiveVelocity', 'rangeChirpWeighting']
        else:
            exclude_args = ['nes0', 'elevationAntennaPattern']

        cp_h5_meta_data(src_h5, dst_h5,
                        os.path.join(src_meta_path, 'processingInformation/parameters'),
                        os.path.join(dst_meta_path, 'processingInformation/parameters'),
                        excludes=exclude_args)

        # Copy calibrationInformation group
        exclude_args = []
        if is_insar:
            exclude_args = ['nes0', 'elevationAntennaPattern']
        for freq in freq_pols.keys():
            frequency = f'frequency{freq}'
            pol_list = freq_pols[freq]
            if pol_list is None:
                continue
            for polarization in pol_list:
                cp_h5_meta_data(src_h5, dst_h5,
                                os.path.join(src_meta_path,
                                             f'calibrationInformation/{frequency}/{polarization}'),
                                os.path.join(dst_meta_path,
                                             f'calibrationInformation/{frequency}/{polarization}'),
                                excludes=exclude_args)

        # Copy product specifics
        if is_insar:
            copy_insar_meta(cfg, dst, src_h5, dst_h5, src_meta_path)
        else:
            copy_gslc_gcov_meta(ref_slc.SwathPath, dst, src_h5, dst_h5)

        src_h5.close()
        dst_h5.close()


def copy_gslc_gcov_meta(src_swath_path, dst, src_h5, dst_h5):
    '''
    Copy metadata info for GSLC GCOV workflows
    '''
    # prelim setup
    common_parent_path = 'science/LSAR'

    for freq in ['A', 'B']:
        ds_ref = f'{src_swath_path}/frequency{freq}'
        if ds_ref not in src_h5:
            continue

        cp_h5_meta_data(src_h5, dst_h5, ds_ref,
                        os.path.join(common_parent_path, f'{dst}/grids/frequency{freq}'),
                        excludes=['acquiredCenterFrequency', 'acquiredAzimuthBandwidth',
                                  'acquiredRangeBandwidth', 'nominalAcquisitionPRF', 'slantRange',
                                  'sceneCenterAlongTrackSpacing', 'sceneCenterGroundRangeSpacing',
                                  'HH', 'HV', 'VH', 'VV', 'RH', 'RV',
                                  'validSamplesSubSwath1', 'validSamplesSubSwath2',
                                  'validSamplesSubSwath3', 'validSamplesSubSwath4',
                                  'listOfPolarizations'],
                        renames={'processedCenterFrequency': 'centerFrequency',
                                 'processedAzimuthBandwidth': 'azimuthBandwidth',
                                 'processedRangeBandwidth': 'rangeBandwidth'})


def copy_insar_meta(cfg, dst, src_h5, dst_h5, src_meta_path):
    '''
    Copy metadata specific to INSAR workflow
    '''
    common_parent_path = 'science/LSAR'
    dst_meta_path = os.path.join(common_parent_path, f'{dst}/metadata')

    secondary_hdf5 = cfg['InputFileGroup']['SecondaryFilePath']
    freq_pols = cfg['processing']['input_subset']['list_of_frequencies']

    # Open secondary SLC
    with h5py.File(secondary_hdf5, 'r', libver='latest', swmr=True) as secondary_h5:

        dst_proc = os.path.join(dst_meta_path, 'processingInformation/parameters')
        src_proc = os.path.join(src_meta_path, 'processingInformation/parameters')

        # Create groups in processing Information
        dst_h5.create_group(os.path.join(dst_proc, 'common'))
        dst_h5.create_group(os.path.join(dst_proc, 'reference'))
        dst_h5.create_group(os.path.join(dst_proc, 'secondary'))

        # Copy data for reference and secondary
        cp_h5_meta_data(src_h5, dst_h5, os.path.join(src_proc, 'effectiveVelocity'),
                        os.path.join(dst_proc, 'reference/effectiveVelocity'))
        cp_h5_meta_data(secondary_h5, dst_h5, os.path.join(src_proc, 'effectiveVelocity'),
                        os.path.join(dst_proc, 'secondary/effectiveVelocity'))
        for freq in freq_pols.keys():
            frequency = f'frequency{freq}'
            cp_h5_meta_data(src_h5, dst_h5, os.path.join(src_proc, f'{frequency}'),
                            os.path.join(dst_proc, f'reference/{frequency}'))
            cp_h5_meta_data(secondary_h5, dst_h5, os.path.join(src_proc, f'{frequency}'),
                            os.path.join(dst_proc, f'secondary/{frequency}'))

        # Copy secondary image slantRange and azimuth time (modify attributes)
        dst_grid_path = os.path.join(dst_meta_path, 'radarGrid')
        if dst in ['RUNW', 'RIFG']:
            dst_grid_path = os.path.join(dst_meta_path, 'geolocationGrid')

        cp_h5_meta_data(secondary_h5, dst_h5, os.path.join(src_meta_path,
                        'geolocationGrid/slantRange'),
                        os.path.join(dst_grid_path, 'secondarySlantRange'))
        cp_h5_meta_data(secondary_h5, dst_h5, os.path.join(src_meta_path,
                        'geolocationGrid/zeroDopplerTime'),
                        os.path.join(dst_grid_path, 'secondaryZeroDopplerAzimuthTime'))

        # Update these attribute with a description
        descr = "Slant range of corresponding pixels in secondary image"
        dst_h5[os.path.join(dst_grid_path, 'secondarySlantRange')].attrs["description"] = descr
        descr = "Zero Doppler azimuth time of corresponding pixel in secondary image"
        dst_h5[os.path.join(dst_grid_path, 'secondaryZeroDopplerAzimuthTime')].attrs["description"] = descr


def prep_ds(cfg, output_hdf5, dst):
    '''
    Prepare datasets for GSLC, GCOV,
    INSAR (GUNW, RIFG, RUNW) workflows
    '''

    # unpack
    with h5py.File(output_hdf5, 'a', libver='latest', swmr=True) as dst_h5:
        # Fork the dataset preparation for GSLC/GCOV and GUNW
        if dst in ['GSLC', 'GCOV']:
            prep_ds_gslc_gcov(cfg, dst, dst_h5)
        else:
            prep_ds_insar(cfg, dst, dst_h5)


def prep_ds_gslc_gcov(cfg, dst, dst_h5):
    '''
    Prepare datasets for GSLC and GCOV
    '''
    # unpack info
    common_parent_path = 'science/LSAR'
    freq_pols = cfg['processing']['input_subset']['list_of_frequencies']

    # Data type
    ctype = h5py.h5t.py_create(np.complex64)
    ctype.commit(dst_h5['/'].id, np.string_('complex64'))

    # Create datasets in the ouput hdf5
    geogrids = cfg['processing']['geocode']['geogrids']
    for freq in freq_pols.keys():
        pol_list = freq_pols[freq]
        shape = (geogrids[freq].length, geogrids[freq].width)
        dst_parent_path = os.path.join(common_parent_path, f'{dst}/grids/frequency{freq}')

        set_get_geo_info(dst_h5, dst_parent_path, geogrids[freq])

        # GSLC specfics datasets
        if dst == 'GSLC':
            for polarization in pol_list:
                dst_grp = dst_h5[dst_parent_path]
                descr = 'Geocoded RSLC for {polarization} channel'
                _create_datasets(dst_grp, shape, ctype, polarization,
                                 descr=descr, units=None, grids="projections")

        # set GCOV polarization values (diagonal values only)
        if dst == 'GCOV':
            pol_list = [(p + p).upper() for p in pol_list]

        _add_polarization_list(dst_h5, dst, common_parent_path, freq, pol_list)


def prep_ds_insar(cfg, dst, dst_h5):
    '''
    prepare INSAR (GUNW, RIFG, RUNW) specific datasets
    '''

    # unpack info
    common_parent_path = 'science/LSAR'
    freq_pols = cfg['processing']['input_subset']['list_of_frequencies']

    # Extract range and azimuth looks
    rg_looks = cfg['processing']['crossmul']['range_looks']
    az_looks = cfg['processing']['crossmul']['azimuth_looks']

    # Create datasets in the ouput hdf5
    geogrids = cfg['processing']['geocode']['geogrids']

    # Create list of frequencies
    id_group = dst_h5['science/LSAR/identification']
    descr = "List of frequency layers available in the product"
    dset = id_group.create_dataset('listOfFrequencies', data=np.string_(list(freq_pols.keys())))
    dset.attrs["description"] = descr

    for freq in freq_pols.keys():
        pol_list = freq_pols[freq]

        if dst in ['RUNW', 'RIFG']:
            grid_swath = 'swaths'

            # Get SLC dimensions for that frequency
            # TO DO (R2): define different shape for offset layer
            input_h5 = cfg['InputFileGroup']['InputFilePath']
            src_h5 = h5py.File(input_h5, 'r', libver='latest', swmr=True)
            dset = src_h5[os.path.join(common_parent_path, f'SLC/swaths/frequency{freq}/HH')]
            az_lines, rg_cols = dset.shape
            shape = (az_lines // az_looks, rg_cols // rg_looks)
        else:
            grid_swath = 'grids'
            shape = (geogrids[freq].length, geogrids[freq].width)

        # Create grid or swath group depending on product
        dst_h5[os.path.join(common_parent_path, f'{dst}')].create_group(grid_swath)
        dst_h5[os.path.join(common_parent_path, f'{dst}/{grid_swath}')].create_group(f'frequency{freq}')
        dst_parent_path = os.path.join(common_parent_path, f'{dst}/{grid_swath}/frequency{freq}')

        if dst in ['RIFG', 'RUNW']:
            # Generate slantRange and Azimuth time (for RIFG and RUNW only)
            slant_range = src_h5[f'science/LSAR/SLC/swaths/frequency{freq}/slantRange'][()]
            doppler_time = src_h5['science/LSAR/SLC/swaths/zeroDopplerTime'][()]

            # TO DO: This is valid for odd number of looks. For R1 extend this to even number of looks
            idx_rg = np.arange(int(len(slant_range) / rg_looks) * rg_looks)[::rg_looks] + int(rg_looks / 2)
            idx_az = np.arange(int(len(doppler_time) / az_looks) * az_looks)[::az_looks] + int(az_looks / 2)

            descr = "CF compliant dimension associated with slant range"
            id_group = dst_h5[os.path.join(common_parent_path, f'{dst}/{grid_swath}/frequency{freq}')]
            dset = id_group.create_dataset('slantRange', data=slant_range[idx_rg])
            dset.attrs["description"] = descr
            dset.attrs["units"] = np.string_("meters")

            descr = descr.replace("slant range", "azimuth time")
            dset = id_group.create_dataset('zeroDopplerTime', data=doppler_time[idx_az])
            dset.attrs["description"] = descr
            dset.attrs["units"] = src_h5['science/LSAR/SLC/swaths/zeroDopplerTime'].attrs["units"]
            src_h5.close()

        # Add list of polarizations
        _add_polarization_list(dst_h5, dst, common_parent_path, freq, pol_list)

        # Add centerFrequency and number of subswaths
        descr = "Center frequency of the processed image"
        _create_datasets(dst_h5[dst_parent_path], [0], np.float32, "centerFrequency",
                         descr=descr, units="Hz")
        descr = "Number of swaths of continuous imagery, due to gaps"
        _create_datasets(dst_h5[dst_parent_path], [0], np.uint8, "numberOfSubSwaths",
                         descr=descr, units=" ")

        # Create path to interferogram and pixelOffsets
        dst_path_intf = os.path.join(dst_parent_path, 'interferogram')
        dst_path_offs = os.path.join(dst_parent_path, 'pixelOffsets')
        dst_h5.create_group(dst_path_intf)
        dst_h5.create_group(dst_path_offs)

        # Add projection
        if dst == "GUNW":
            set_get_geo_info(dst_h5, dst_parent_path, geogrids[freq])
        # TO DO R2: Different projection for pixel offset
        # TO DO R2: different x/yCoordinates and spacing for pixel Offset

        # Add scalar dataset to interferogram (common to HH and VV)
        descr = "Processed azimuth bandwidth in Hz"
        _create_datasets(dst_h5[dst_path_intf], [0], np.float32, 'azimuthBandwidth',
                         descr=descr, units="Hz")
        _create_datasets(dst_h5[dst_path_intf], [0], np.float32, 'rangeBandwidth',
                         descr=descr.replace("azimuth", "range"), units="Hz")
        descr = " Averaging window size in pixels in azimuth direction for covariance \
                          matrix estimation"
        _create_datasets(dst_h5[dst_path_intf], [0], np.uint8, 'numberOfAzimuthLooks',
                         descr=descr, units=" ", data=az_looks)
        _create_datasets(dst_h5[dst_path_intf], [0], np.uint8, 'numberOfRangeLooks',
                         descr=descr.replace("azimuth", "slant range"), units=" ", data=rg_looks)
        descr = "Slant range spacing of grid. Same as difference between \
                         consecutive samples in slantRange array"
        _create_datasets(dst_h5[dst_path_intf], [0], np.uint8, 'slantRangeSpacing',
                         descr=descr, units="meters")
        descr = "Time interval in the along track direction for raster layers. " \
                "This is the same as the spacing between consecutive entries in " \
                "zeroDopplerTime array"
        _create_datasets(dst_h5[dst_path_intf], [0], np.float32, 'zeroDopplerTimeSpacing',
                         descr=descr, units="seconds")

        if dst in ['RIFG', 'RUNW']:
            descr = "Nominal along track spacing in meters between consecutive lines" \
                    "near mid swath of the interferogram image"
            _create_datasets(dst_h5[dst_parent_path], [0], np.float32, "sceneCenterAlongTrackSpacing",
                             descr=descr, units="meters")
            descr = descr.replace("Nominal along track", "Nominal ground range").replace('lines', 'pixels')
            _create_datasets(dst_h5[dst_parent_path], [0], np.float32, "sceneCenterGroundRangeSpacing",
                             descr=descr, units="meters")

            # Valid subsamples: to be copied from RSLC or need to be created from scratch?
            descr = " First and last valid sample in each line of 1st subswath"
            _create_datasets(dst_h5[dst_parent_path], [2], np.uint8, "validSubSamplesSubSwath1",
                             descr=descr, units=" ")
            _create_datasets(dst_h5[dst_parent_path], [2], np.uint8, "validSubSamplesSubSwath2",
                             descr=descr.replace('1st', '2nd'), units=" ")
            _create_datasets(dst_h5[dst_parent_path], [2], np.uint8, "validSubSamplesSubSwath3",
                             descr=descr.replace('1st', '3rd'), units=" ")
            _create_datasets(dst_h5[dst_parent_path], [2], np.uint8, "validSubSamplesSubSwath4",
                             descr=descr.replace('1st', '4th'), units=" ")

        # Adding scalar datasets to pixelOffsets group
        descr = "Along track window size for cross-correlation"
        _create_datasets(dst_h5[dst_path_offs], [0], np.uint8, 'alongTrackWindowSize',
                         descr=descr, units="pixels")
        _create_datasets(dst_h5[dst_path_offs], [0], np.uint8, 'slantRangeWindowSize',
                         descr=descr.replace("Along track", "Slant range"), units="pixels")
        descr = "Along track skip window size for cross-correlation"
        _create_datasets(dst_h5[dst_path_offs], [0], np.uint8, 'alongTrackSkipWindowSize',
                         descr=descr, units="pixels")
        _create_datasets(dst_h5[dst_path_offs], [0], np.uint8, 'slantRangeSkipWindowSize',
                         descr=descr.replace("Along track ", "Slant range"), units="pixels")
        descr = "Along track search window size for cross-correlation"
        _create_datasets(dst_h5[dst_path_offs], [0], np.uint8, 'alongTrackSearchWindowSize',
                         descr=descr, units="pixels")
        _create_datasets(dst_h5[dst_path_offs], [0], np.uint8, 'slantRangeSearchWindowSize',
                         descr=descr.replace("Along track ", "Slant range"), units="pixels")
        descr = "Oversampling factor of the cross-correlation surface"
        _create_datasets(dst_h5[dst_path_offs], [0], np.uint8, 'correlationSurfaceOversampling',
                         descr=descr, units=" ")
        descr = "Method used for generating pixel offsets"
        _create_datasets(dst_h5[dst_path_offs], [9], np.string_, 'crossCorrelationMethod',
                         descr=descr, units=None)

        # Adding polarization-dependent datasets to interferogram and pixelOffsets
        for pol in pol_list:
            intf_path = os.path.join(dst_path_intf, f'{pol}')
            offs_path = os.path.join(dst_path_offs, f'{pol}')

            dst_h5.create_group(intf_path)
            dst_h5.create_group(offs_path)

            if dst in ['GUNW', 'RUNW']:
                descr = f"Connected components for {pol} layer"
                _create_datasets(dst_h5[intf_path], shape, np.uint8, 'connectedComponents',
                                 descr=descr, units=" ")
                descr = f"Unwrapped interferogram between {pol} layers"
                _create_datasets(dst_h5[intf_path], shape, np.float32, 'unwrappedPhase',
                                 descr=descr, units="radians")
                descr = f"Phase sigma coherence between {pol} layers"
                _create_datasets(dst_h5[intf_path], shape, np.float32, 'phaseSigmaCoherence',
                                 descr=descr, units=" ")
                descr = "Ionosphere phase screen"
                _create_datasets(dst_h5[intf_path], shape, np.float32, 'ionospherePhaseScreen',
                                 chunks=(128, 128),
                                 descr=descr, units="radians")
                descr = "Uncertainty of split spectrum ionosphere phase screen"
                _create_datasets(dst_h5[intf_path], shape, np.float32, 'ionospherePhaseScreenUncertainty',
                                 chunks=(128, 128),
                                 descr=descr, units="radians")
                if dst == "GUNW":
                    descr = f"Coherence mask for {pol} layer"
                    _create_datasets(dst_h5[intf_path], shape, np.float32, 'coherenceMask',
                                     descr=descr, units=" ")
            else:
                descr = f"Interferogram between {pol} layers"
                _create_datasets(dst_h5[intf_path], shape, np.complex64, "wrappedPhase",
                                 chunks=(128, 128),
                                 descr=descr, units="radians")
                if (az_looks, rg_looks) != (1,1):
                    descr = f"Coherence between {pol} layers"
                    _create_datasets(dst_h5[intf_path], shape, np.float32, "phaseSigmaCoherence",
                                     chunks=(128, 128),
                                     descr=descr, units=None)

            # Add pixel offset datasets
            descr = f"Along track offset for {pol} layer"
            _create_datasets(dst_h5[offs_path], shape, np.float32, 'alongTrackOffset',
                             descr=descr, units="meters")
            _create_datasets(dst_h5[offs_path], shape, np.float32, 'slantRangeOffset',
                             descr=descr.replace("Along track", "Slant range"), units="meters")
            descr = " Correlation metric"
            _create_datasets(dst_h5[offs_path], shape, np.float32, 'correlation',
                             descr=descr, units=" ")

        # Add datasets in metadata
        dst_cal = os.path.join(common_parent_path, f'{dst}/metadata/calibrationInformation')
        dst_proc = os.path.join(common_parent_path, f'{dst}/metadata/processingInformation/parameters')
        dst_grid = os.path.join(common_parent_path, f'{dst}/metadata/radarGrid')

        if dst in ['RUNW', 'RIFG']:
            dst_grid = os.path.join(common_parent_path, f'{dst}/metadata/geolocationGrid')

        # Add parallel and perpendicular component of baseline.
        # TO DO (R2): Define dimension of baseline LUTs
        descr = "Perpendicular component of the InSAR baseline"
        _create_datasets(dst_h5[dst_grid], shape, np.float64, "perpendicularBaseline",
                         descr=descr, units="meters")
        _create_datasets(dst_h5[dst_grid], shape, np.float64, "parallelBaseline",
                         descr=descr.replace('Perpendicular', 'Parallel'), units="meters")

        dst_cal_group = f'{dst_cal}/frequency{freq}'

        descr = "Bulk along track time offset used to align reference and secondary image"
        _create_datasets(dst_h5[dst_cal_group], [0], np.float32, "bulkAlongTrackTimeOffset",
                         descr=np.string_(descr), units="seconds")
        _create_datasets(dst_h5[dst_cal_group], [0], np.float32, "bulkSlantRangeOffset",
                         descr=np.string_(descr.replace('along track', 'slant range')), units="seconds")

        # Add datasets in processingInformation/parameters/common
        dst_common_group = f'{dst_proc}/common/frequency{freq}'
        dst_h5.create_group(dst_common_group)

        descr = " Common Doppler bandwidth used for processing the interferogram"
        _create_datasets(dst_h5[dst_common_group], [0], np.float64, "dopplerBandwidth",
                         descr=descr, units="Hz")
        descr = f" 2D LUT of Doppler Centroid for frequency {freq}"
        _create_datasets(dst_h5[dst_common_group], shape, np.float64, "dopplerCentroid",
                         descr=descr, units="Hz")
        descr = "Number of looks applied in along track direction"
        _create_datasets(dst_h5[dst_common_group], [0], np.uint8, "numberOfAzimuthLooks",
                         descr=descr, units=" ", data=int(az_looks))
        _create_datasets(dst_h5[dst_common_group], [0], np.uint8, "numberOfRangeLooks",
                         descr=descr.replace("along track", "slant range"), units=" ", data=int(rg_looks))

        if dst == "RIFG":
            descr = "Reference elevation above WGS84 Ellipsoid used for flattening"
            _create_datasets(dst_h5[dst_common_group], [0], np.float32, "referenceFlatteningElevation",
                             descr=descr, units="meters")

        for pol in pol_list:
            cal_path = os.path.join(dst_cal_group, f"{pol}")
            descr = "Constant wrapped reference phase used to balance the interferogram"
            _create_datasets(dst_h5[cal_path], [0], np.float32, "referencePhase",
                             descr=descr, units="radians")


def _create_datasets(dst_grp, shape, ctype, dataset_name,
                     chunks=(128, 128), descr=None, units=None, grids=None, data=None):
    if len(shape) == 1:
        if ctype == np.string_:
            ds = dst_grp.create_dataset(dataset_name, data=np.string_("         "))
        else:
            ds = dst_grp.create_dataset(dataset_name, dtype=ctype, data=data)
    else:
        if chunks[0] < shape[0] and chunks[1] < shape[1]:
            ds = dst_grp.create_dataset(dataset_name, dtype=ctype, shape=shape, chunks=chunks)
        else:
            ds = dst_grp.create_dataset(dataset_name, dtype=ctype, shape=shape)

    ds.attrs['description'] = np.string_(descr)

    if units is not None:
        ds.attrs['units'] = np.string_(units)

    if grids is not None:
        ds.attrs['grid_mapping'] = np.string_(grids)


def _add_polarization_list(dst_h5, dst, common_parent_path, frequency, pols):
    '''
    Add list of processed polarizations
    '''
    dataset_path = os.path.join(common_parent_path, f'{dst}/grids/frequency{frequency}')

    if dst in ['RUNW', 'RIFG']:
        dataset_path = os.path.join(common_parent_path, f'{dst}/swaths/frequency{frequency}')

    grp = dst_h5[dataset_path]
    name = "listOfPolarizations"
    pols_array = np.array(pols, dtype="S2")
    dset = grp.create_dataset(name, data=pols_array)
    desc = f"List of polarization layers with frequency{frequency}"
    dset.attrs["description"] = np.string_(desc)


def set_get_geo_info(hdf5_obj, root_ds, geo_grid):
    epsg_code = geo_grid.epsg

    dx = geo_grid.spacing_x
    x0 = geo_grid.start_x + 0.5 * dx
    xf = x0 + (geo_grid.width - 1) * dx
    x_vect = np.linspace(x0, xf, geo_grid.width, dtype=np.float64)

    dy = geo_grid.spacing_y
    y0 = geo_grid.start_y + 0.5 * dy
    yf = y0 + (geo_grid.length - 1) * dy
    y_vect = np.linspace(y0, yf, geo_grid.length, dtype=np.float64)

    hdf5_obj.attrs['Conventions'] = np.string_("CF-1.8")

    if epsg_code == 4326:
        x_coord_units = "degree_east"
        y_coord_units = "degree_north"
        x_standard_name = "longitude"
        y_standard_name = "latitude"
    else:
        x_coord_units = "m"
        y_coord_units = "m"
        x_standard_name = "projection_x_coordinate"
        y_standard_name = "projection_y_coordinate"

    # xCoordinateSpacing
    descr = (f'Nominal spacing in {x_coord_units}'
             ' between consecutive pixels')

    xds_spacing_name = os.path.join(root_ds, 'xCoordinateSpacing')
    if xds_spacing_name in hdf5_obj:
        del hdf5_obj[xds_spacing_name]
    xds_spacing = hdf5_obj.create_dataset(xds_spacing_name, data=dx)
    xds_spacing.attrs["description"] = np.string_(descr)
    xds_spacing.attrs["units"] = np.string_(x_coord_units)

    # yCoordinateSpacing
    descr = (f'Nominal spacing in {y_coord_units}'
             ' between consecutive lines')

    yds_spacing_name = os.path.join(root_ds, 'yCoordinateSpacing')
    if yds_spacing_name in hdf5_obj:
        del hdf5_obj[yds_spacing_name]
    yds_spacing = hdf5_obj.create_dataset(yds_spacing_name, data=dy)
    yds_spacing.attrs["description"] = np.string_(descr)
    yds_spacing.attrs["units"] = np.string_(y_coord_units)

    # xCoordinates
    descr = "CF compliant dimension associated with the X coordinate"
    xds_name = os.path.join(root_ds, 'xCoordinates')
    if xds_name in hdf5_obj:
        del hdf5_obj[xds_name]
    xds = hdf5_obj.create_dataset(xds_name, data=x_vect)
    xds.attrs['standard_name'] = x_standard_name
    xds.attrs["description"] = np.string_(descr)
    xds.attrs["units"] = np.string_(x_coord_units)

    # yCoordinates
    descr = "CF compliant dimension associated with the Y coordinate"
    yds_name = os.path.join(root_ds, 'yCoordinates')
    if yds_name in hdf5_obj:
        del hdf5_obj[yds_name]
    yds = hdf5_obj.create_dataset(yds_name, data=y_vect)
    yds.attrs['standard_name'] = y_standard_name
    yds.attrs["description"] = np.string_(descr)
    yds.attrs["units"] = np.string_(y_coord_units)

    coordinates_list = [xds, yds]

    try:
        for _ds in coordinates_list:
            _ds.make_scale()
    except AttributeError:
        pass

    # Associate grid mapping with data - projection created later
    projection_ds_name = os.path.join(root_ds, "projection")

    # Create a new single int dataset for projections
    if projection_ds_name in hdf5_obj:
        del hdf5_obj[projection_ds_name]
    projds = hdf5_obj.create_dataset(projection_ds_name, (), dtype='i')
    projds[()] = epsg_code

    # Set up osr for wkt
    srs = osr.SpatialReference()
    srs.ImportFromEPSG(epsg_code)

    # WGS84 ellipsoid
    projds.attrs['semi_major_axis'] = 6378137.0
    projds.attrs['inverse_flattening'] = 298.257223563
    projds.attrs['ellipsoid'] = np.string_("WGS84")

    # Additional fields
    projds.attrs['epsg_code'] = epsg_code

    # CF 1.7+ requires this attribute to be named "crs_wkt"
    # spatial_ref is old GDAL way. Using that for testing only.
    # For NISAR replace with "crs_wkt"
    projds.attrs['spatial_ref'] = np.string_(srs.ExportToWkt())

    # Here we have handcoded the attributes for the different cases
    # Recommended method is to use pyproj.CRS.to_cf() as shown above
    # To get complete set of attributes.

    sr = osr.SpatialReference()
    sr.ImportFromEPSG(epsg_code)

    projds.attrs['grid_mapping_name'] = sr.GetName()

    # Set up units
    # Geodetic latitude / longitude
    if epsg_code == 4326:
        # Set up grid mapping
        projds.attrs['longitude_of_prime_meridian'] = 0.0
        projds.attrs['latitude_of_projection_origin'] = sr.GetProjParm(osr.SRS_PP_LATITUDE_OF_ORIGIN)
        projds.attrs['longitude_of_projection_origin'] = sr.GetProjParm(osr.SRS_PP_LONGITUDE_OF_ORIGIN)

    else:
        # UTM zones
        if ((epsg_code > 32600 and
             epsg_code < 32661) or
                (epsg_code > 32700 and
                 epsg_code < 32761)):
            # Set up grid mapping
            projds.attrs['utm_zone_number'] = epsg_code % 100

        # Polar Stereo North
        elif epsg_code == 3413:
            # Set up grid mapping
            projds.attrs['standard_parallel'] = 70.0
            projds.attrs['straight_vertical_longitude_from_pole'] = -45.0

        # Polar Stereo south
        elif epsg_code == 3031:
            # Set up grid mapping
            projds.attrs['standard_parallel'] = -71.0
            projds.attrs['straight_vertical_longitude_from_pole'] = 0.0

        # EASE 2 for soil moisture L3
        elif epsg_code == 6933:
            # Set up grid mapping
            projds.attrs['longitude_of_central_meridian'] = 0.0
            projds.attrs['standard_parallel'] = 30.0

        # Europe Equal Area for Deformation map (to be implemented in isce3)
        elif epsg_code == 3035:
            # Set up grid mapping
            projds.attrs['standard_parallel'] = -71.0
            projds.attrs['straight_vertical_longitude_from_pole'] = 0.0

        else:
            raise NotImplementedError(f'EPSG {epsg_code} waiting for implementation / not supported in ISCE3')

        # Setup common parameters
        xds.attrs['long_name'] = np.string_("x coordinate of projection")
        yds.attrs['long_name'] = np.string_("y coordinate of projection")

        projds.attrs['false_easting'] = sr.GetProjParm(osr.SRS_PP_FALSE_EASTING)
        projds.attrs['false_northing'] = sr.GetProjParm(osr.SRS_PP_FALSE_NORTHING)

        projds.attrs['latitude_of_projection_origin'] = sr.GetProjParm(osr.SRS_PP_LATITUDE_OF_ORIGIN)
        projds.attrs['longitude_of_projection_origin'] = sr.GetProjParm(osr.SRS_PP_LONGITUDE_OF_ORIGIN)

    return yds, xds