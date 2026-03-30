# pyCycle Upstream TODO

## 1. Submit numpy 2.x compatibility PR to OpenMDAO/pyCycle

**References:** OpenMDAO/pyCycle#116, OpenMDAO/pyCycle#77 (prior art)

**What:** The pyCycle CEA and tabular thermo modules crash on numpy 2.x due to two classes of breaking changes:

- `np.complex` alias removed in numpy 2.0 → replace with `np.complex128`
- Shape-(1,) OpenMDAO inputs can no longer be implicitly assigned to scalar array positions → use `.item()`

**Patch file:** `scripts/pycycle-numpy2.patch` contains the complete fix.

**Files changed (4):**

| File | Lines | Fix |
|------|-------|-----|
| `pycycle/thermo/cea/chem_eq.py` | 294, 296 | `np.complex` → `np.complex128` |
| `pycycle/thermo/cea/props_rhs.py` | 99 | `inputs['n_moles']` → `.item()` |
| `pycycle/thermo/cea/props_rhs.py` | 114, 115 | `np.complex` → `np.complex128` |
| `pycycle/thermo/cea/props_calcs.py` | 63, 112 | `inputs['n_moles']` → `.item()` |
| `pycycle/thermo/tabular/thermo_add.py` | 121 | `W_other_mix` → `.item()` |

**Steps to submit the PR:**

1. Fork `OpenMDAO/pyCycle` to your GitHub account
2. Clone the fork, create a branch: `git checkout -b fix/numpy2-compat`
3. Apply the patch: `git apply /path/to/scripts/pycycle-numpy2.patch`
4. Commit with message:
   ```
   Fix numpy 2.x compatibility in CEA and tabular thermo

   - Replace removed np.complex alias with np.complex128 (chem_eq.py, props_rhs.py)
   - Use .item() for shape-(1,) OpenMDAO inputs assigned to scalar array
     positions (props_calcs.py, props_rhs.py, thermo_add.py)

   Fixes #116
   ```
5. Push and open PR against `OpenMDAO/pyCycle:master`
6. In the PR description, note:
   - References issue #116 (which only identified thermo_add.py)
   - This PR fixes the broader scope: CEA thermo (props_calcs, props_rhs, chem_eq) + tabular (thermo_add)
   - All fixes are backward-compatible with numpy 1.x
   - Tested with numpy 2.4.4, OpenMDAO 3.41.0, pyCycle 4.4.1-dev
   - Prior art: PR #77 fixed the same class of issue in the HBTF example

## 2. After PR merges: clean up local patch

1. Remove the patch-apply block from `scripts/setup-upstream.sh`
2. Delete `scripts/pycycle-numpy2.patch`
3. Run `scripts/setup-upstream.sh` to verify fresh clone works without patch
4. Run `uv run python -m pytest packages/pyc/tests/ packages/pyc/examples/turbojet/tests/ --rootdir=. -v` to confirm
