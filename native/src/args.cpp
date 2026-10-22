#include "bhlab/pipeline.hpp"

#include <cstdlib>
#include <stdexcept>
#include <string>

#include "bhlab/layout.hpp"

namespace bhlab {
namespace {

std::string option(int argc, char** argv, const std::string& name, const std::string& fallback) {
  for (int i = 1; i < argc; ++i) {
    const std::string arg = argv[i];
    if (arg == name && i + 1 < argc) return argv[i + 1];
    const std::string prefix = name + "=";
    if (arg.rfind(prefix, 0) == 0) return arg.substr(prefix.size());
  }
  return fallback;
}

bool flag(int argc, char** argv, const std::string& name) {
  for (int i = 1; i < argc; ++i) {
    if (std::string(argv[i]) == name) return true;
  }
  return false;
}

}  // namespace

PipelineSpec parse_args(int argc, char** argv) {
  PipelineSpec spec;
  spec.app = option(argc, argv, "--app", "kmer");
  spec.input = option(argc, argv, "--input", "");
  spec.output = option(argc, argv, "--output", "");
  spec.events = option(argc, argv, "--events", "events.jsonl");
  spec.job_id = option(argc, argv, "--job-id", "");
  if (spec.job_id.empty()) {
    const char* env = std::getenv("BHLAB_JOB_ID");
    spec.job_id = env != nullptr ? env : "local";
  }
  spec.layout = parse_layout(option(argc, argv, "--layout", "aos8"));
  const std::string device = option(argc, argv, "--device", "cpu");
  if (device == "gpu") {
    spec.device = Device::GPU;
  } else if (device == "cpu") {
    spec.device = Device::CPU;
  } else {
    throw std::runtime_error("device must be cpu or gpu: " + device);
  }
  spec.k = std::stoi(option(argc, argv, "--k", "21"));
  spec.window = std::stoi(option(argc, argv, "--window", "10"));
  spec.threads = std::stoi(option(argc, argv, "--threads", "1"));
  const std::string max_reads = option(argc, argv, "--max-reads", "0");
  spec.max_reads = static_cast<std::size_t>(std::stoull(max_reads));
  spec.verify_shuffle = flag(argc, argv, "--verify-shuffle");
  if (spec.input.empty()) throw std::runtime_error("--input is required");
  if (spec.output.empty()) throw std::runtime_error("--output is required");
  return spec;
}

}  // namespace bhlab
