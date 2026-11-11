#!/usr/bin/env python3
"""Writes the APG-M8 configuration: auif_m8/definitions/construction_definitions.json (status PROPOSED), auif_m8/definitions/apg_canonical_model.json (status PROPOSED) and
one CANDIDATE translation pack per Builder Zero integration in auif_m8/packs/.  Deterministic: running it again writes the same bytes (a test checks the stored files).
The schema fingerprint each pack accepts is AUIF's own fingerprint (auif.discovery.fingerprint) of AUIF's own file importer's discovery of the Builder Zero folder; it must be
the same for every tenant that has the folder, or the tool stops.
Usage: python3 -I tools/make_m8_config.py [--check]     (--check: compare with the stored files, write nothing; exit 1 on any difference)"""
import json, os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.dont_write_bytecode = True
sys.path.insert(0, ROOT)
from apg_auif import dependency, definitions as DEF, layout, pack as PK          # noqa: E402


def dumps(o):
    return json.dumps(o, indent=1, sort_keys=True, ensure_ascii=True) + '\n'


def build():
    dependency.ensure()
    defs = DEF.construction_definitions(ROOT)
    model = DEF.model(defs)
    from auif.canonical import CanonicalModel
    CanonicalModel(model)                                                          # the AUIF contract accepts it
    tpl, byent, files = DEF.load_templates(ROOT), DEF.by_entity(defs), {}
    files['definitions/construction_definitions.json'] = defs
    files['definitions/apg_canonical_model.json'] = model
    for iid, info in layout.integrations().items():
        fps, ents = set(), None
        for tenant in sorted(os.listdir(os.path.join(ROOT, 'builder_zero'))):
            if not os.path.isdir(os.path.join(ROOT, 'builder_zero', tenant, info['folder'])) or tenant in ('scenarios',):
                continue
            specs = PK.file_specs(ROOT, tenant, iid, tpl)
            if not specs:
                continue
            if ents is None or len(specs) > len(ents):
                ents = list(specs)
            fps.add((tuple(specs), PK.fingerprint_of(PK.connector(ROOT, tenant, iid, tpl, specs))))
        full = [fp for e, fp in fps if list(e) == ents]
        if len(set(full)) != 1:
            raise SystemExit('integration %s: the tenants do not share one schema fingerprint: %s' % (iid, sorted(fps)))
        p = PK.build_pack(iid, byent, ents, full)
        from auif.contracts import validate
        validate('translation#TranslationPack', p)
        if PK.form_problems(p):
            raise SystemExit('the contract reference form is violated: %s' % PK.form_problems(p)[:3])
        files['packs/%s.json' % p['pack_id']] = p
    return files


def main():
    files = build()
    check = '--check' in sys.argv
    bad = []
    for rel, obj in sorted(files.items()):
        path = os.path.join(ROOT, 'auif_m8', rel)
        text = dumps(obj)
        if check:
            if not os.path.exists(path) or open(path, encoding='utf-8').read() != text:
                bad.append(rel)
        else:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            open(path, 'w', encoding='utf-8', newline='\n').write(text)
    have = sorted(os.path.relpath(os.path.join(d, f), os.path.join(ROOT, 'auif_m8')).replace(os.sep, '/') for d, _, fs in os.walk(os.path.join(ROOT, 'auif_m8', 'packs')) for f in fs)
    extra = [h for h in have if h not in files]
    if check:
        print('config files %d, differing %d, unexpected %d' % (len(files), len(bad), len(extra)) + (' %r' % (bad + extra) if bad or extra else ''))
        return 1 if bad or extra else 0
    print('wrote %d config files' % len(files))
    return 0


if __name__ == '__main__':
    sys.exit(main())
