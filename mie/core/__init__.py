"""The MIE-1 core (specification MIE1_SPEC.md v0.3).  Pure and deterministic: it reads no clock, random source, network, file system or environment, and it imports only the
Python standard library.  Field meaning lives only in packs.  The service entry point is mie.core.engine.Engine; the reference (in-memory, non-production) ports are in
mie.core.reference."""
