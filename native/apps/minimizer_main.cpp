#include "bhlab/pipeline.hpp"

int main(int argc, char** argv) {
  bhlab::PipelineSpec spec = bhlab::parse_args(argc, argv);
  spec.app = "minimizer";
  return bhlab::run_local(spec);
}
