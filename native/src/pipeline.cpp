#include "bhlab/pipeline.hpp"

#include <chrono>
#include <filesystem>
#include <iostream>
#include <map>
#include <stdexcept>
#include <string>

#include "bhlab/events.hpp"
#include "bhlab/kmer.hpp"
#include "bhlab/layout.hpp"
#include "bhlab/minimizer.hpp"

#if defined(__APPLE__)
#include <sys/resource.h>
#else
#include <sys/resource.h>
#endif

namespace bhlab {
namespace {

double peak_rss_mb() {
  struct rusage usage {};
  getrusage(RUSAGE_SELF, &usage);
#if defined(__APPLE__)
  return static_cast<double>(usage.ru_maxrss) / (1024.0 * 1024.0);
#else
  return static_cast<double>(usage.ru_maxrss) / 1024.0;
#endif
}

double elapsed_seconds(std::chrono::steady_clock::time_point start) {
  const auto end = std::chrono::steady_clock::now();
  return std::chrono::duration<double>(end - start).count();
}

}  // namespace

int run_local(const PipelineSpec& spec) {
  const auto start = std::chrono::steady_clock::now();
  EventLogger events(spec.events, spec.job_id);
  try {
    const std::uintmax_t input_bytes = std::filesystem::file_size(spec.input);
    events.emit("run_start", "info", "local run",
                {{"app", spec.app},
                 {"comm", "local"},
                 {"device", spec.device == Device::GPU ? "gpu" : "cpu"},
                 {"layout", layout_name(spec.layout)},
                 {"input_bytes", std::to_string(input_bytes)},
                 {"k", std::to_string(spec.k)},
                 {"ranks", "1"}});
    if (!spec.steps.empty()) {
      std::string joined;
      for (const std::string& step : spec.steps) {
        if (!joined.empty()) joined += ",";
        joined += step;
      }
      events.emit("pipeline", "info", "pipeline steps", {{"steps", joined}});
    }

    const SeqBatch batch = load_fastx(spec.input, spec.layout, spec.max_reads);
    if (spec.app == "kmer") {
      const auto counted = count_kmers(batch, spec.k, spec.device, spec.threads);
      write_counts_tsv(spec.output, counted, spec.k);
      events.emit("phase_end", "info", "kmer count",
                  {{"phase", "count"},
                   {"seconds", std::to_string(elapsed_seconds(start))},
                   {"kmers", std::to_string(counted.size())},
                   {"reads", std::to_string(batch.size())},
                   {"skipped_reads", std::to_string(batch.skipped_reads)}});
    } else if (spec.app == "minimizer") {
      const auto mins = compute_minimizers(batch, spec.k, spec.window);
      write_minimizers_tsv(spec.output, mins, spec.k);
      events.emit("phase_end", "info", "minimizer sketch",
                  {{"phase", "minimizer"},
                   {"seconds", std::to_string(elapsed_seconds(start))},
                   {"minimizers", std::to_string(mins.size())},
                   {"reads", std::to_string(batch.size())},
                   {"skipped_reads", std::to_string(batch.skipped_reads)}});
    } else {
      throw std::runtime_error("unknown app: " + spec.app);
    }
    events.emit("run_end", "info", "local run complete",
                {{"exit_code", "0"},
                 {"duration_s", std::to_string(elapsed_seconds(start))},
                 {"peak_rss_mb", std::to_string(peak_rss_mb())},
                 {"output", spec.output}});
    return 0;
  } catch (const std::exception& error) {
    try {
      events.emit("error", "error", error.what(),
                  {{"exit_code", "1"}, {"duration_s", std::to_string(elapsed_seconds(start))}});
    } catch (...) {
    }
    std::cerr << "bhlab: " << error.what() << '\n';
    return 1;
  }
}

}  // namespace bhlab
