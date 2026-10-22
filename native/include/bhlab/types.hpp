#pragma once

#include <cstddef>
#include <cstdint>
#include <string>
#include <vector>

namespace bhlab {

enum class Layout { AoS8, SoA2 };
enum class Device { CPU, GPU };

struct SeqBatch {
  Layout layout = Layout::AoS8;
  std::vector<std::string> ids;
  std::vector<std::string> seqs;
  std::vector<std::vector<uint64_t>> packed;
  std::vector<uint32_t> lengths;
  std::size_t skipped_reads = 0;

  std::size_t size() const { return ids.size(); }
  std::size_t total_bases() const;
};

struct KmerCount {
  uint64_t kmer = 0;
  uint32_t count = 0;
  KmerCount() = default;
  KmerCount(uint64_t value, uint32_t occurrences) : kmer(value), count(occurrences) {}
};

struct Minimizer {
  uint32_t read_index = 0;
  uint32_t pos = 0;
  uint64_t hash = 0;
  Minimizer() = default;
  Minimizer(uint32_t read, uint32_t position, uint64_t value)
      : read_index(read), pos(position), hash(value) {}
};

struct PipelineSpec {
  std::string app = "kmer";
  std::string input;
  std::string output;
  std::string events = "events.jsonl";
  std::string job_id = "local";
  Layout layout = Layout::AoS8;
  Device device = Device::CPU;
  int k = 21;
  int window = 10;
  int threads = 1;
  std::size_t max_reads = 0;
  bool verify_shuffle = false;
  std::vector<std::string> steps;
};

}  // namespace bhlab
