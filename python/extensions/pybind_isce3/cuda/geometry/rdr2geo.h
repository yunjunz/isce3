#pragma once

#include <iscecuda/geometry/Topo.h>
#include <pybind11/pybind11.h>

void addbinding(pybind11::class_<isce::cuda::geometry::Topo>&);