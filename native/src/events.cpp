#include "bhlab/events.hpp"

#include <chrono>
#include <ctime>
#include <filesystem>
#include <iomanip>
#include <sstream>
#include <stdexcept>
#include <unistd.h>

namespace bhlab {
namespace {

std::string escape(const std::string& value) {
  std::string out;
  out.reserve(value.size() + 8);
  for (char c : value) {
    switch (c) {
      case '"': out += "\\\""; break;
      case '\\': out += "\\\\"; break;
      case '\n': out += "\\n"; break;
      case '\r': out += "\\r"; break;
      case '\t': out += "\\t"; break;
      default:
        if (static_cast<unsigned char>(c) < 0x20) {
          std::ostringstream code;
          code << "\\u" << std::hex << std::setw(4) << std::setfill('0')
               << static_cast<int>(static_cast<unsigned char>(c));
          out += code.str();
        } else {
          out += c;
        }
    }
  }
  return out;
}

}  // namespace

std::string iso8601_now() {
  const auto now = std::chrono::system_clock::now();
  const std::time_t seconds = std::chrono::system_clock::to_time_t(now);
  std::tm utc{};
  gmtime_r(&seconds, &utc);
  char buffer[32];
  std::strftime(buffer, sizeof(buffer), "%Y-%m-%dT%H:%M:%SZ", &utc);
  return buffer;
}

std::string hostname() {
  char buffer[256] = {0};
  if (gethostname(buffer, sizeof(buffer) - 1) != 0) return "unknown";
  return buffer;
}

EventLogger::EventLogger(const std::string& path, const std::string& job_id)
    : job_id_(job_id), host_(hostname()) {
  const std::filesystem::path target(path);
  if (target.has_parent_path()) std::filesystem::create_directories(target.parent_path());
  out_.open(path, std::ios::out | std::ios::trunc);
  if (!out_) throw std::runtime_error("cannot open event log " + path);
}

void EventLogger::emit(const std::string& event, const std::string& level,
                       const std::string& message,
                       const std::map<std::string, std::string>& params) {
  out_ << "{\"ts\":\"" << iso8601_now() << "\",\"source\":\"app\",\"job_id\":\""
       << escape(job_id_) << "\",\"host\":\"" << escape(host_) << "\",\"event\":\""
       << escape(event) << "\",\"level\":\"" << escape(level) << "\",\"message\":\""
       << escape(message) << "\",\"params\":{";
  bool first = true;
  for (const auto& entry : params) {
    if (!first) out_ << ',';
    first = false;
    out_ << '"' << escape(entry.first) << "\":\"" << escape(entry.second) << '"';
  }
  out_ << "}}\n";
  out_.flush();
}

}  // namespace bhlab
