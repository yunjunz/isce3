#pragma once

#include <string>

namespace isce3 { namespace error {

/** Return code type indicating the exit status of an ISCE operation */
enum class ErrorCode {
    Success = 0,
    OrbitInterpSizeError,
    OrbitInterpDomainError,
    OrbitInterpUnknownMethod,
    FailedToConverge,
    WrongLookSide,
    OutOfBoundsLookup,
};

/** Return a string describing the error code */
std::string getErrorString(ErrorCode);

}} // namespace isce3::error