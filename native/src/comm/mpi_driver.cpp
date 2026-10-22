#include "bhlab/pipeline.hpp"

#include <algorithm>
#include <cstdint>
#include <filesystem>
#include <map>
#include <stdexcept>
#include <string>
#include <unordered_map>
#include <vector>

#include "bhlab/events.hpp"
#include "bhlab/kmer.hpp"
#include "bhlab/layout.hpp"

#ifdef BHLAB_HAVE_MPI
#include <mpi.h>
#endif

namespace bhlab {
#ifdef BHLAB_HAVE_MPI
namespace {

struct Pair {
  uint64_t kmer;
  uint32_t count;
};

SeqBatch slice_batch(const SeqBatch& batch, int rank, int size) {
  SeqBatch out;
  out.layout = batch.layout;
  out.skipped_reads = 0;
  for (std::size_t i = static_cast<std::size_t>(rank); i < batch.size();
       i += static_cast<std::size_t>(size)) {
    out.ids.push_back(batch.ids[i]);
    out.lengths.push_back(batch.lengths[i]);
    if (batch.layout == Layout::AoS8) {
      out.seqs.push_back(batch.seqs[i]);
    } else {
      out.packed.push_back(batch.packed[i]);
    }
  }
  return out;
}

std::vector<Pair> to_pairs(const std::vector<KmerCount>& counts) {
  std::vector<Pair> out;
  out.reserve(counts.size());
  for (const KmerCount& row : counts) out.push_back({row.kmer, row.count});
  return out;
}

std::unordered_map<uint64_t, uint32_t> merge_pairs(const std::vector<Pair>& pairs) {
  std::unordered_map<uint64_t, uint32_t> merged;
  for (const Pair& pair : pairs) merged[pair.kmer] += pair.count;
  return merged;
}

std::vector<KmerCount> sorted_counts(const std::unordered_map<uint64_t, uint32_t>& merged) {
  std::vector<KmerCount> out;
  out.reserve(merged.size());
  for (const auto& entry : merged) out.push_back({entry.first, entry.second});
  std::sort(out.begin(), out.end(),
            [](const KmerCount& a, const KmerCount& b) { return a.kmer < b.kmer; });
  return out;
}

bool same_counts(const std::vector<KmerCount>& a, const std::vector<KmerCount>& b) {
  if (a.size() != b.size()) return false;
  for (std::size_t i = 0; i < a.size(); ++i) {
    if (a[i].kmer != b[i].kmer || a[i].count != b[i].count) return false;
  }
  return true;
}

}  // namespace

int run_mpi(const PipelineSpec& spec) {
  MPI_Init(nullptr, nullptr);
  int rank = 0;
  int size = 1;
  MPI_Comm_rank(MPI_COMM_WORLD, &rank);
  MPI_Comm_size(MPI_COMM_WORLD, &size);

  int rc = 0;
  try {
    const SeqBatch full = load_fastx(spec.input, spec.layout, spec.max_reads);
    const SeqBatch local = slice_batch(full, rank, size);
    const std::vector<KmerCount> local_counts =
        count_kmers(local, spec.k, spec.device, spec.threads);

    const std::vector<Pair> local_pairs = to_pairs(local_counts);
    std::vector<int> send_counts(static_cast<std::size_t>(size), 0);
    for (const Pair& pair : local_pairs) {
      ++send_counts[static_cast<std::size_t>(pair.kmer % static_cast<uint64_t>(size))];
    }
    std::vector<int> recv_counts(static_cast<std::size_t>(size), 0);
    MPI_Alltoall(send_counts.data(), 1, MPI_INT, recv_counts.data(), 1, MPI_INT, MPI_COMM_WORLD);

    std::vector<int> send_displs(static_cast<std::size_t>(size), 0);
    std::vector<int> recv_displs(static_cast<std::size_t>(size), 0);
    std::vector<int> cursor(static_cast<std::size_t>(size), 0);
    for (int i = 1; i < size; ++i) {
      send_displs[static_cast<std::size_t>(i)] =
          send_displs[static_cast<std::size_t>(i - 1)] + send_counts[static_cast<std::size_t>(i - 1)];
      recv_displs[static_cast<std::size_t>(i)] =
          recv_displs[static_cast<std::size_t>(i - 1)] + recv_counts[static_cast<std::size_t>(i - 1)];
    }
    cursor = send_displs;

    std::vector<Pair> send_pairs(static_cast<std::size_t>(send_displs.back() + send_counts.back()));
    for (const Pair& pair : local_pairs) {
      const std::size_t dest = static_cast<std::size_t>(pair.kmer % static_cast<uint64_t>(size));
      send_pairs[static_cast<std::size_t>(cursor[dest]++)] = pair;
    }

    const int total_recv = recv_displs.back() + recv_counts.back();
    std::vector<Pair> recv_pairs(static_cast<std::size_t>(total_recv));
    std::vector<int> send_bytes(static_cast<std::size_t>(size), 0);
    std::vector<int> recv_bytes(static_cast<std::size_t>(size), 0);
    std::vector<int> send_byte_displs(static_cast<std::size_t>(size), 0);
    std::vector<int> recv_byte_displs(static_cast<std::size_t>(size), 0);
    for (int i = 0; i < size; ++i) {
      send_bytes[static_cast<std::size_t>(i)] =
          send_counts[static_cast<std::size_t>(i)] * static_cast<int>(sizeof(Pair));
      recv_bytes[static_cast<std::size_t>(i)] =
          recv_counts[static_cast<std::size_t>(i)] * static_cast<int>(sizeof(Pair));
      send_byte_displs[static_cast<std::size_t>(i)] =
          send_displs[static_cast<std::size_t>(i)] * static_cast<int>(sizeof(Pair));
      recv_byte_displs[static_cast<std::size_t>(i)] =
          recv_displs[static_cast<std::size_t>(i)] * static_cast<int>(sizeof(Pair));
    }
    MPI_Alltoallv(send_pairs.data(), send_bytes.data(), send_byte_displs.data(), MPI_BYTE,
                  recv_pairs.data(), recv_bytes.data(), recv_byte_displs.data(), MPI_BYTE,
                  MPI_COMM_WORLD);

    const std::unordered_map<uint64_t, uint32_t> merged = merge_pairs(recv_pairs);
    const std::vector<KmerCount> merged_counts = sorted_counts(merged);
    const std::vector<Pair> merged_pairs = to_pairs(merged_counts);

    int local_merged = static_cast<int>(merged_pairs.size());
    std::vector<int> gathered_counts(static_cast<std::size_t>(size), 0);
    MPI_Gather(&local_merged, 1, MPI_INT, gathered_counts.data(), 1, MPI_INT, 0, MPI_COMM_WORLD);
    std::vector<int> gathered_displs(static_cast<std::size_t>(size), 0);
    for (int i = 1; i < size; ++i) {
      gathered_displs[static_cast<std::size_t>(i)] =
          gathered_displs[static_cast<std::size_t>(i - 1)] +
          gathered_counts[static_cast<std::size_t>(i - 1)];
    }
    const int total_gathered = gathered_displs.back() + gathered_counts.back();
    std::vector<Pair> gathered_pairs(static_cast<std::size_t>(total_gathered));
    std::vector<int> gathered_bytes(static_cast<std::size_t>(size), 0);
    std::vector<int> gathered_byte_displs(static_cast<std::size_t>(size), 0);
    for (int i = 0; i < size; ++i) {
      gathered_bytes[static_cast<std::size_t>(i)] =
          gathered_counts[static_cast<std::size_t>(i)] * static_cast<int>(sizeof(Pair));
      gathered_byte_displs[static_cast<std::size_t>(i)] =
          gathered_displs[static_cast<std::size_t>(i)] * static_cast<int>(sizeof(Pair));
    }
    MPI_Gatherv(merged_pairs.data(), local_merged * static_cast<int>(sizeof(Pair)), MPI_BYTE,
                gathered_pairs.data(), gathered_bytes.data(), gathered_byte_displs.data(), MPI_BYTE,
                0, MPI_COMM_WORLD);

    if (rank == 0) {
      const std::unordered_map<uint64_t, uint32_t> final_map = merge_pairs(gathered_pairs);
      const std::vector<KmerCount> final_counts = sorted_counts(final_map);
      write_counts_tsv(spec.output, final_counts, spec.k);

      EventLogger events(spec.events, spec.job_id);
      std::string steps_joined;
      for (const std::string& step : spec.steps) {
        if (!steps_joined.empty()) steps_joined += ",";
        steps_joined += step;
      }
      events.emit("run_start", "info", "mpi run",
                  {{"app", spec.app},
                   {"steps", steps_joined},
                   {"comm", "mpi"},
                   {"device", spec.device == Device::GPU ? "gpu" : "cpu"},
                   {"layout", layout_name(spec.layout)},
                   {"input_bytes", std::to_string(std::filesystem::file_size(spec.input))},
                   {"k", std::to_string(spec.k)},
                   {"ranks", std::to_string(size)}});
      events.emit("shuffle_end", "info", "kmer shuffle",
                  {{"phase", "shuffle"},
                   {"messages", std::to_string(size)},
                   {"bytes", std::to_string(send_pairs.size() * sizeof(Pair))},
                   {"kmers", std::to_string(final_counts.size())}});
      if (spec.verify_shuffle) {
        const std::vector<KmerCount> serial =
            count_kmers(full, spec.k, Device::CPU, 1);
        const bool match = same_counts(serial, final_counts);
        events.emit("verify", match ? "info" : "error", "serial comparison",
                    {{"match", match ? "1" : "0"}});
        if (!match) rc = 2;
      }
      events.emit("run_end", rc == 0 ? "info" : "error", "mpi run complete",
                  {{"exit_code", std::to_string(rc)}, {"output", spec.output}});
    }
    MPI_Bcast(&rc, 1, MPI_INT, 0, MPI_COMM_WORLD);
  } catch (const std::exception& error) {
    if (rank == 0) {
      try {
        EventLogger events(spec.events, spec.job_id);
        events.emit("error", "error", error.what(), {{"exit_code", "1"}});
      } catch (...) {
      }
    }
    rc = 1;
  }
  MPI_Finalize();
  return rc;
}
#else
int run_mpi(const PipelineSpec&) {
  throw std::runtime_error("MPI support was not compiled in; rebuild with the cpu-gcc profile");
}
#endif
}  // namespace bhlab
