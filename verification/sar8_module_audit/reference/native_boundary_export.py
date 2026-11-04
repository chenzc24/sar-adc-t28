"""Analysis-only boundary recovery. Python 2.7/3; source run is read-only."""
from __future__ import print_function
import argparse
import hashlib
import json
import math
import os
import re
import subprocess
import zlib
try:
    STRING_TYPES = (basestring,)
except NameError:
    STRING_TYPES = (str,)


def inside(path, root):
    path, root = os.path.normcase(os.path.realpath(path)), os.path.normcase(os.path.realpath(root))
    return path == root or path.startswith(root + os.sep)


def validate_paths(run, output, source):
    run, output, source = [os.path.realpath(p) for p in (run, output, source)]
    if inside(run, source) or inside(source, run):
        raise ValueError("new run and source run must be disjoint")
    if os.path.normcase(output) == os.path.normcase(run) or not inside(output, run) or inside(output, source):
        raise ValueError("output must be strictly inside new run, outside source")
    if not os.path.isdir(run) or not os.path.isdir(source):
        raise ValueError("run/source directories must exist")
    return run, output, source


def safe_file(root, relative):
    if not isinstance(relative, STRING_TYPES) or os.path.isabs(relative) or ".." in relative.replace("\\", "/").split("/"):
        raise ValueError("unsafe relative path")
    path = os.path.realpath(os.path.join(root, relative))
    if not inside(path, root) or not os.path.isfile(path):
        raise ValueError("required file missing or outside declared root: " + relative)
    return path


def small_json(path):
    if os.path.getsize(path) > 1024 * 1024:
        raise ValueError("metadata input exceeds1MiB")
    with open(path) as stream:
        return json.load(stream)


def digest(path):
    h = hashlib.sha256()
    with open(path, "rb") as stream:
        while True:
            block = stream.read(65536)
            if not block:
                break
            h.update(block)
    return h.hexdigest()


def finite(value):
    return isinstance(value, (float, int)) and not isinstance(value, bool) and not (math.isnan(value) or math.isinf(value))


def validate_manifest(m):
    if m.get("schema_version") != 1 or m.get("boundary_start_s") != 0:
        raise ValueError("schema1 and t=0 history required")
    for key in ["boundary_end_s", "minimum_cover_s", "diagnostic_start_s", "diagnostic_end_s"]:
        if not finite(m.get(key)):
            raise ValueError("undefined extraction time: " + key)
    if not (0 < m["minimum_cover_s"] <= m["boundary_end_s"]
            and 0 <= m["diagnostic_start_s"] < m["diagnostic_end_s"] <= m["boundary_end_s"]):
        raise ValueError("invalid native extraction intervals")
    for key in ["max_total_output_bytes", "max_boundary_gzip_bytes", "max_diagnostic_bytes"]:
        if type(m.get(key)) is not int or m[key] <= 0:
            raise ValueError("explicit output budgets required")
    if m["max_total_output_bytes"] >= 32 * 1024 * 1024:
        raise ValueError("total output must remain below32MiB")
    boundary = m.get("required_boundary_signals")
    diagnostic = m.get("diagnostic_signals")
    if not isinstance(boundary, list) or not boundary or not isinstance(diagnostic, list) or not diagnostic:
        raise ValueError("required native boundary/diagnostic lists missing")
    try:
        basestring_type = basestring
    except NameError:
        basestring_type = str
    def valid_name(name):
        return isinstance(name, basestring_type) and re.match(r"^[a-z0-9_!.:]+$", name) is not None and name != "time"
    if not all(valid_name(x) for x in boundary) or len(set(boundary)) != len(boundary):
        raise ValueError("invalid or duplicate boundary name")
    if any(not isinstance(x, dict) or set(x) != set(["name", "required"])
           or not valid_name(x["name"]) or type(x["required"]) is not bool for x in diagnostic):
        raise ValueError("invalid diagnostic signal")
    if len(set(x["name"] for x in diagnostic)) != len(diagnostic):
        raise ValueError("duplicate diagnostic signal")


def output_size(folder):
    return sum(os.path.getsize(os.path.join(folder, n)) for n in os.listdir(folder)
               if os.path.isfile(os.path.join(folder, n)))


def export(run, output, source):
    run, output, source = validate_paths(run, output, source)
    manifest_path = safe_file(run, "inputs/native_boundary_export.json")
    cpp = safe_file(run, "inputs/native_boundary_stream.cpp")
    m = small_json(manifest_path)
    validate_manifest(m)
    if os.path.basename(source) != m["source_run_id"]:
        raise ValueError("unexpected source run identity")
    state = small_json(safe_file(source, "simulation.state.json"))
    if state.get("status") != "complete" or state.get("exit_code") != 0:
        raise ValueError("source simulation must be completed/exit0")
    status = safe_file(source, "raw/logStatus")
    with open(status) as stream:
        if not re.search(r"\b" + re.escape(m["source_analysis_name"]) + r"\s+PASS\b", stream.read(65536)):
            raise ValueError("source native PASS missing")
    for name, expected in m["source_input_hashes"].items():
        if digest(safe_file(source, name)) != expected:
            raise ValueError("source input hash mismatch: " + name)
    raw = safe_file(source, m["raw_relative_path"])
    raw_before = os.stat(raw)
    if os.path.exists(output) and os.listdir(output):
        raise ValueError("new output directory must be empty; preserve previous artifacts")
    if not os.path.isdir(output):
        os.makedirs(output)
    prefix = os.path.join(output, "native")
    boundary_list = os.path.join(output, "boundary.list")
    diagnostic_list = os.path.join(output, "diagnostic.list")
    with open(boundary_list, "w") as stream:
        stream.write("\n".join(m["required_boundary_signals"]) + "\n")
    with open(diagnostic_list, "w") as stream:
        stream.write("\n".join(("%d %s" % (int(x["required"]), x["name"])) for x in m["diagnostic_signals"]) + "\n")
    exe = os.path.join(output, "native_boundary_stream.exe" if os.name == "nt" else "native_boundary_stream")
    build_log = os.path.join(output, "build.log")
    with open(build_log, "wb") as stream:
        subprocess.check_call([os.environ.get("CXX", "g++"), "-O2", "-std=c++11", cpp, "-o", exe],
                              cwd=output, stdout=stream, stderr=stream)
    reserve = 128 * 1024
    gzip_limit = min(m["max_boundary_gzip_bytes"],
                     m["max_total_output_bytes"] - output_size(output) - m["max_diagnostic_bytes"] - reserve)
    if gzip_limit <= 0:
        raise ValueError("output budget cannot fit compiled parser plus diagnostic reserve")
    command = [exe, raw, boundary_list, diagnostic_list, prefix,
               "%.17g" % m["boundary_end_s"], "%.17g" % m["diagnostic_start_s"],
               "%.17g" % m["diagnostic_end_s"], str(m["max_diagnostic_bytes"]),
               "%.17g" % m["minimum_cover_s"]]
    def limits():
        import resource
        resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
        cap = int(m["parser_address_space_limit_mib"]) * 1024 * 1024
        resource.setrlimit(resource.RLIMIT_AS, (cap, cap))
    gzip_path = os.path.join(output, "boundary.f64le.gz")
    uncompressed_hash, compressed_hash = hashlib.sha256(), hashlib.sha256()
    raw_bytes, compressed_bytes = 0, 0
    compressor = zlib.compressobj(1, zlib.DEFLATED, 31)
    process = None
    with open(os.path.join(output, "parser.stderr"), "wb") as errors, open(gzip_path, "wb") as target:
        try:
            kwargs = dict(cwd=output, stdout=subprocess.PIPE, stderr=errors)
            if os.name == "posix":
                kwargs["preexec_fn"] = limits
            process = subprocess.Popen(command, **kwargs)
            while True:
                data = process.stdout.read(65536)
                if not data:
                    break
                raw_bytes += len(data)
                uncompressed_hash.update(data)
                encoded = compressor.compress(data)
                if compressed_bytes + len(encoded) > gzip_limit:
                    raise ValueError("lossless boundary output budget exceeded; no decimation fallback")
                target.write(encoded)
                compressed_hash.update(encoded)
                compressed_bytes += len(encoded)
            encoded = compressor.flush()
            if compressed_bytes + len(encoded) > gzip_limit:
                raise ValueError("lossless boundary output budget exceeded at flush")
            target.write(encoded)
            compressed_hash.update(encoded)
            compressed_bytes += len(encoded)
            process.stdout.close()
            if process.wait() != 0:
                raise ValueError("native parser failed; see parser.stderr")
        except Exception:
            if process is not None and process.poll() is None:
                process.kill()
                process.wait()
            if process is not None and not process.stdout.closed:
                process.stdout.close()
            raise
    raw_after = os.stat(raw)
    if (raw_before.st_size, raw_before.st_mtime) != (raw_after.st_size, raw_after.st_mtime):
        raise ValueError("source raw changed during extraction")
    meta = small_json(prefix + ".meta.json")
    if raw_bytes != meta["native_points_exported"] * meta["boundary_columns"] * 8:
        raise ValueError("incomplete binary rows")
    if meta["first_time_s"] != 0 or meta["last_native_time_s"] < m["minimum_cover_s"]:
        raise ValueError("native initial-to-fault history incomplete")
    result = dict(analysis_complete=True, electrical_verdict="not_inferred",
                  scope="Native boundary recovery only; no replay or circuit qualification",
                  source_run_dir=source, source_raw_relative_path=m["raw_relative_path"],
                  source_raw_bytes=raw_before.st_size, source_raw_mtime=raw_before.st_mtime,
                  source_raw_sha256=None, source_raw_hash_note="Raw is streamed only to cutoff; not read again for full-file SHA",
                  source_input_hashes=m["source_input_hashes"],
                  manifest_sha256=digest(manifest_path), parser_source_sha256=digest(cpp),
                  native=meta, boundary_uncompressed_bytes=raw_bytes,
                  boundary_uncompressed_sha256=uncompressed_hash.hexdigest(),
                  boundary_gzip_bytes=compressed_bytes, boundary_gzip_sha256=compressed_hash.hexdigest(),
                  source_PSF_END_note="May be false because extraction stops after native lookahead beyond cutoff; source PASS/exit0 checked separately",
                  missing_historical_currents=m.get("not_requested_because_unsaved", []),
                  managed_rss_limit_mib=m["managed_rss_limit_mib"], interpolation=False, decimation=False)
    result["diagnostic_sha256"] = digest(prefix + ".diagnostic.f64le")
    if output_size(output) + reserve > m["max_total_output_bytes"]:
        raise ValueError("aggregate output budget exceeded")
    result_path = os.path.join(output, "result.json")
    with open(result_path, "w") as stream:
        json.dump(result, stream, indent=2)
        stream.write("\n")
    if output_size(output) >= 32 * 1024 * 1024:
        raise ValueError("aggregate collection budget exceeded")
    print("NATIVE_BOUNDARY_EXPORT_OK", meta["native_points_exported"], compressed_bytes)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--source-run-dir", required=True)
    args = parser.parse_args()
    export(args.run_dir, args.output_dir, args.source_run_dir)


if __name__ == "__main__":
    main()
