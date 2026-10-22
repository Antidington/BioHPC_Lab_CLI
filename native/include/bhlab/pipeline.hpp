#pragma once

#include "bhlab/types.hpp"

namespace bhlab {

PipelineSpec parse_args(int argc, char** argv);
int run_local(const PipelineSpec& spec);
int run_mpi(const PipelineSpec& spec);

}  // namespace bhlab
