# PolyHok Integration
> Local PolyHok dependency with Nx and a CUDA NIF

Entry: `mix.exs:deps()`
Flow: path dependency → PolyHok NIF → Nx tensor copied to GPU → tensor copied back

Source: `/home/daniel/poly_hok`
- Local fork remote: `dpnunez/poly_hok`
- Upstream reference: `ardubois/poly_hok`
- CUDA 13.3 support present in local fork

NIF loading: `/home/daniel/poly_hok/lib/poly_hok.ex:load_nifs()`
- Must resolve `gpu_nifs` through `:code.priv_dir(:poly_hok)`
- A cwd-relative `./priv/gpu_nifs` fails when PolyHok is a Mix dependency

Native dependency: `deps/matrex/Makefile`
- `MATREX_BLAS=noblas mix deps.compile` works for the Nx-only integration
- OpenBLAS alternative requires the system development headers

Verification: `test/poly_hok_test.exs`
- Requires direct NVIDIA GPU access; restricted sandboxes block NVML/CUDA

NDVI prototype reuse: `/home/daniel/poly_hok/lib/poly_hok/ske.ex:Ske.map2/3`
- `Ske.map2_kernel/5` already uses one linear thread index, a bounds check and one output allocation
- `Ske.map2/3` preserves the Nx shape and launches one element-wise kernel for two GPU inputs
- Exact `NaN` materialization inside PolyHok-generated CUDA remains unverified and must be proved before choosing the final kernel expression

Updated: 2026-09-02
