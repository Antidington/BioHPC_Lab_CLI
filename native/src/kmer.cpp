#include "bhlab/kmer.hpp"

#include <algorithm>
#include <stdexcept>
#include <unordered_map>
#include <vector>

#include "bhlab/layout.hpp"

#ifdef _OPENMP
#include <omp.h>
#endif

namespace bhlab {
namespace {

uint64_t kmer_mask(int k) {
  if (k <= 0 || k > 31) throw std::runtime_error("k must be between 1 and 31");
  return (1ULL << (2 * k)) - 1ULL;
}

void count_one_read(const SeqBatch& batch, std::size_t read_index, int k, uint64_t mask,
                    std::unordered_map<uint64_t, uint32_t>& table) {
  const std::size_t length = batch.lengths[read_index];
  if (length < static_cast<std::size_t>(k)) return;
  uint64_t forward = 0;
  for (std::size_t pos = 0; pos < length; ++pos) {
    forward = ((forward << 2) | base_at(batch, read_index, pos)) & mask;
    if (pos + 1 >= static_cast<std::size_t>(k)) {
      const uint64_t reverse = reverse_complement(forward, k);
      ++table[std::min(forward, reverse)];
    }
  }
}

std::vector<KmerCount> finalize(const std::unordered_map<uint64_t, uint32_t>& table) {
  std::vector<KmerCount> counts;
  counts.reserve(table.size());
  for (const auto& entry : table) counts.push_back({entry.first, entry.second});
  std::sort(counts.begin(), counts.end(),
            [](const KmerCount& a, const KmerCount& b) { return a.kmer < b.kmer; });
  return counts;
}

}  // namespace

std::vector<KmerCount> count_kmers_cpu(const SeqBatch& batch, int k, int threads) {
  const uint64_t mask = kmer_mask(k);
#ifdef _OPENMP
  const int worker_count = (threads > 0) ? threads : omp_get_max_threads();
  if (worker_count > 1) {
    std::vector<std::unordered_map<uint64_t, uint32_t>> locals(
        static_cast<std::size_t>(worker_count));
#pragma omp parallel for schedule(static) num_threads(worker_count)
    for (std::int64_t i = 0; i < static_cast<std::int64_t>(batch.size()); ++i) {
      const int tid = omp_get_thread_num();
      count_one_read(batch, static_cast<std::size_t>(i), k, mask,
                     locals[static_cast<std::size_t>(tid)]);
    }
    std::unordered_map<uint64_t, uint32_t> merged;
    for (const auto& local : locals) {
      for (const auto& entry : local) merged[entry.first] += entry.second;
    }
    return finalize(merged);
  }
#else
  (void)threads;
#endif
  std::unordered_map<uint64_t, uint32_t> table;
  for (std::size_t i = 0; i < batch.size(); ++i) count_one_read(batch, i, k, mask, table);
  return finalize(table);
}

std::vector<KmerCount> count_kmers(const SeqBatch& batch, int k, Device device, int threads) {
  if (device == Device::GPU) {
#ifdef BHLAB_HAVE_CUDA
    return count_kmers_gpu(batch, k);
#else
    throw std::runtime_error("GPU support was not compiled in; rebuild with the gpu-cuda profile");
#endif
  }
  return count_kmers_cpu(batch, k, threads);
}

}  // namespace bhlab
