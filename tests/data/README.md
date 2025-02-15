# Test Data

This README gives brief descriptions on the generation of various test data
found in this directory.

## Winnipeg

- The original product from which the test data are generated: winnip_31604_12061_004_120717_L090_CX_129_05.h5
  This is a UAVSAR NISAR simulated product. Check science/LSAR/identification/productVersion to get the product version
  As for NISAR data/ Simulated NISAR data have to be intended as zero-doppler

- All winnipeg-related "reference" products in this folder (e.g. warped_winnipeg.slc) have been generated using ISCE2 v2.3.
  The ISCE2 processing uses "winnip_31604_12061_004_120717_L090_CX_129_05.h5" as reference and secondary SLC to create the golden/reference dataset.

## Attitude

Attitude sample data in NISAR format (see JPL D-102264) was provided by the
G&C team (Dave Bates, et al) during NASA Internal Thread Test 04 (NITT-04)
activities in late 2020/early 2021. The hash of the original file delivered
by email is

```
$ md5sum NISAR_ANC_L_PR_FRP_20210114T023357_20200107T200000_20200109T040000.xml
2101bddf088d3b4e8e0e3051931f8284  NISAR_ANC_L_PR_FRP_20210114T023357_20200107T200000_20200109T040000.xml
```

To reduce the size of the test data, this file was trimmed to the first ten
records to produce `attitude.xml`.

## Orbit

Orbit sample data in NISAR format (see JPL D-102253) provided by Paul Ries
via email on 2020-07-06. It was generated from Jason2 data. The hash of the
original file is

```
$ md5sum -b smoothFinal.xml.gz
f415fc38e1feff0bb1453782be3d2b5f *smoothFinal.xml.gz
```

This file was uncompressed and trimmed to the first ten state vectors in
order to reduce the size of the `orbit.xml` file stored here.

# nisar_129_gcov_crop.h5

Minimal GCOV sample product obtained from processing a small subset of the
UAVSAR dataset NISARA_13905_19070_007_190930_L090_CX_129_02 from the AM/PM
campaing. The sample product was generated with parameters:
```
top_left:
   y_abs: 35.18
   x_abs: -83.46
bottom_right:
   y_abs: 35.13
   x_abs: -83.41
```
## REE

Multi-channel L0B Raw data and HDF5 antenna pattern cuts (NISAR antenna format *v2*) 
initially generated by Radar Echo Emulator tool, [*REE*](https://github.jpl.nasa.gov/SALSA-REE/REE_SRC), 
and then post-processed and converted into L0B product via its python utility tool
[*ReeUtilPy*](https://github.jpl.nasa.gov/SALSA-REE/ReeUtilPy).
Note that these files may be stored in a separate location outside *isce3* repo.

- **REE_L0B_out17.h5**

  Simplest possible point target simulation: single target, uniform PRF, no
  noise, zero Doppler geometry.  Designed to test backproject and focus.py.
  REE input file preserved here (REE_L0B_out17.rdf).  Orbit and attitude data
  were dumped to NISAR XML format files in the `focus` subdirectory, which
  also contains a runconfig file for focus.py.  The target is located at
  longitude -54.579586258 deg, latitude 3.177088785 deg, height 0.0 m.  The
  file was generated using REE v14.8.6 and ReeUtilPy v2.9.4.

- **REE_RSLC_out17.h5**

  This is an RSLC product generated from the "out17" L0B data.  It only covers
  a small chip around the target and can be used for testing the point target
  analysis software.

- **REE_ANTPAT_CUTS_BEAM4.h5**

  Four-beam *NISAR* antenna pattern file. The original full *2-D* version of patterns
  come from datasets for case of *Case4g19c* generated by NISAR antenna team and stored 
  on *JPL NISE* machine.
  This file contains the first four NISAR-like beams (nearest range ones).
  It containes both elevation and azimuth cuts of both polarizations *H* and *V*.
  The file is generated along with the L0B files "REE_L0B_CHANNEL4_EXTSCENE_PASS1...".
  That is the same antenna patterns used to generate the respective 4-channel L0B 
  products.

- **REE_L0B_CHANNEL4_EXTSCENE_PASS1_LINE3000_CALIB.h5**

  Truncated version of first pass of repeat-pass four-channel *V*-polarized NISAR-like
  simulated *REE* L0B product over heterogenous urban-like simulated extended scene.
  The total number of truncated range lines is *3000*.
  The range bins has also been truncated from original datasets to get rid of far-range 
  bins where there exist simply noise plus TX gap. The number of range bins is 1850.
  This dataset is suitable for demonstrating formation of three null patterns in elevation 
  direction used in elevation pointing over heterogenous scene.
  The caltone has been already applied to individual RX channels via RxCal prior to its
  L0B file generation. Thus, RX channels are balanced out.
  Echo dataset has a shape of channel-by-rangeline-by-rangebin.
  This dataset is useful to test EL null-range product generation.

- **REE_L0B_CHANNEL4_EXTSCENE_PASS1_LINE3000_UNCALIB.h5**

  Similar to "REE_L0B_CHANNEL4_EXTSCENE_PASS1_LINE3000_CALIB.h5" with exception of no
  RxCal (caltone) has been applied. Thus, the RX channels are imbalance!
  This dataset is useful to test generation of EL null-range product with caltone flag.

- **REE_ORBIT_CHANNEL4_EXTSCENE_PASS1.xml**

  External Orbit XML file covering original full version of dataset 
  "REE_L0B_CHANNEL4_EXTSCENE_PASS1_LINE3000_CALIB.h5".
  The format is based on doc JPL D-102253.

- **REE_ATTITUDE_CHANNEL4_EXTSCENE_PASS1.xml**

  External Attitude XML file covering original full version of dataset 
  "REE_L0B_CHANNEL4_EXTSCENE_PASS1_LINE3000_CALIB.h5".
  The format is based on doc JPL D-102253.

- **REE_L0B_DBF_EXTSCENE_PASS1_LINE3000_TRUNCATED.h5**

  DBFed version of "REE_L0B_CHANNEL4_EXTSCENE_PASS1_LINE3000_CALIB.h5" 
  under subdir *pointing/*.

- **REE_ANTPAT_CUTS_DBF.h5**

  Antenna pattern with DBFed data for L0B product 
  "REE_L0B_CHANNEL4_EXTSCENE_PASS1_LINE3000_CALIB.h5" under subdir *pointing/*.

- **REE_ORBIT_DATA_DBF_PASS1.xml**
  
  External orbit file for L0B product "REE_L0B_CHANNEL4_EXTSCENE_PASS1_LINE3000_CALIB.h5" 
  under subdir *pointing/*.

- **REE_ATTITUDE_DATA_DBF_PASS1.xml**
  
  External attitude file for L0B product "REE_L0B_CHANNEL4_EXTSCENE_PASS1_LINE3000_CALIB.h5" 
  under subdir *pointing/*.

## ALOS1

- **ALOS1_PALSAR_ANTPAT_FIVE_BEAMS.h5**

  Antenna pattern cuts (NISAR antenna format *v2*) for five beams centered at off-nadir 
  angle around *34.0 deg*. 
  The elevation-cuts for several beams are provided by *ESA* via M. Lavalle
  while the azimuth-cut is simply generated by H. Ghaemi from *Fig.3*[1].

- **ALPSRP081257070-H1.0__A_HH_2500_LINES.h5**

  L0B-formatted *HH* raw *PALSAR* data collected by *ALOS1* over Amazon rain forest.
  This dataset corresponds to beam # *7* of *ALOS1* centered at off-nadir angle around 
  *34.0 deg*. This data corresponds to beam/channel # *3* in the above HDF5 antenna file.
  There are total *2500* range lines.
  The scene is cosidered homogenous suitable for antenna pattern measurement in 
  elevation direction.

- **ALOS1_PALSAR_ANTPAT_BEAM343.h5**

  Antenna pattern for beam # *7* of *ALOS1* whose zero-degree EL corresponds to  off-nadir 
  angle around *34.3 deg*. The antenna pattern EL/AZ cuts are interpolated/smoothed version
  provided by *ESA*.

- **ALPSRP264757150-H1.0__A_HH_LINE4000-5000_RANGE0-2200.h5**

  Truncated ALOS1 PALSAR L0B product containing simply *HH* product with 1000 range lines 
  within [4000,5000) and 2200 range bins within [0, 2200) over the Amazon.

## Beamformer
Multi-channel L0B Raw data and HDF5 antenna pattern cuts (NISAR antenna format *v2*) 
initially generated by Radar Echo Emulator tool, [*REE*](https://github.jpl.nasa.gov/SALSA-REE/REE_SRC), 
and then post-processed and converted into L0B product via its python utility tool
[*ReeUtilPy*](https://github.jpl.nasa.gov/SALSA-REE/ReeUtilPy).

- **REE_ANTPAT_CUTS_DATA.h5**

  Twelve-beam *NISAR* antenna pattern file. The original full *2-D* version of patterns
  come from datasets for case of *Case4g20*.
  It containes both elevation and azimuth cuts of both polarizations *H* and *V*.

- **REE_L0B_ECHO_DATA.h5**

  This raw data set is *H*-polarized NISAR-like simulated *REE* L0B product.
  The total number of range lines is *70*. The total number of range bins is 28927. 
  The Tx range lines types are of HPA, LNA, and BYPASS. BYPASS range line interval is 20.


## Geoid EGM96

- **egm96_15.gtx**
  The geoid raster "egm96_15.gtx" contains the global geoid EGM96 array
  sampled at 0.25 degrees in latitude and longitude. The raster
  is geolocated over geographic coordinates with longitude range 
  varying from -180 to 180 degrees.
    
- **egm96_15_lon_0_360.gtx**
  The geoid raster "egm96_15_lon_0_360.gtx" is the "shifted" version of
  "egm96_15.gtx" geolocated over geographic coordinates with longitude
  from 0 to 360 deg.


[1]: M. Shimada et al., "PALSAR Radiometric and Geometric Calibration",
*IEEE Trans. Geosci. Remote Sens.*, pp. 3915-3932, December 2009.

## DEM
- **dem_himalayas_E81p5_N28p3_short.tiff**

  DEM raster file over a very small area of Himalayas downloaded from NISAR-DEM AWS S3
  bucket as follows:
  ```
  $ stage_dem.py -b 81.45 28.29 81.5 28.3 -o dem_himalayas_E81p5_N28p3_short.vrt
  ```

## Point Target

- **search_first_null.pkl**

  Python pickle archive of a slice of a point target impulse response function
  in dB as well as the index of the peak.  This is an example from a point
  target simulation where the analysis script once failed to find the null
  width.
