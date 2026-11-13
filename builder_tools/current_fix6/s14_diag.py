"""S14 diagnostic (builder, NOT the AM4-1 evidence, NOT INDEPENDENT): M10's own run_one on the three ids of M10's EQUIV, one at a time
(1 worker), each timed, to see whether M10 lets them survive when the machine is not overloaded.  Run from an extraction of the freeze."""
import json, os, shutil, sys, tempfile, time
import importlib.util
spec = importlib.util.spec_from_file_location('m2_mutants_m10', os.path.join(os.getcwd(), 'tools', 'm2_mutants.py'))
M = importlib.util.module_from_spec(spec); spec.loader.exec_module(M)
ids = sorted(k for k, v in M.EQUIV.items() if v)
out = []
for m in M.MUT:
    if m[0] in ids:
        tmp = tempfile.mkdtemp(prefix='m2_diag_')
        t = time.time()
        try:
            r = M.run_one(m, tmp)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
        out.append({'id': m[0], 'result': list(r), 'seconds': round(time.time() - t, 1)})
        print(json.dumps(out[-1]), flush=True)
print(json.dumps({'equiv': ids, 'results': out}))
