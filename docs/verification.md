# Verification record · 0.1.0 review build

The initial local test run executed **60 tests successfully**. **Two optional VBT Pro runtime tests were skipped** because that dependency was not installed in the build environment. They are included for execution in a separately licensed environment. No claim of licensed-runtime validation is made for this build.

Fresh-environment CI exposed a timestamp-unit assumption in fold construction. The implementation now compares intervals in matching units and normalizes timestamps for data hashing. Four additional regression cases cover seconds, milliseconds, microseconds and nanoseconds, bringing the suite to 64 reference test cases plus two optional licensed-runtime cases. The CI matrix covers Python 3.11/3.13 and pandas 2/3. Consult the Actions run for the particular commit rather than treating this document as a live CI status badge.

Checks cover candidate identity, input permutation stability, LHS stratification, malformed OHLC, incomplete resampling, half-open windows, indicator hand calculations, prefix invariance for all six core variants, documented PinBar boundary differences, duplicate/out-of-order callbacks, IH bid/ask order-level math, stop/target ambiguity, gap fills, stage-end exits, costs, result caching, configuration changes, writer locks, empty shortlists and full-demo resume.

The demo's eager and progressive shortlists were compared directly. A separate run repeated from cache. Both successful and empty-shortlist outputs are tested. The original working repository and live systems are not involved in any runtime test.

A package build/install check and publication-boundary scan accompany the review. The scan is a best-effort check of this candidate release, not an exhaustive forensic scan of another repository's history or a guarantee that no independently useful idea is disclosed.

Before an external release, execute the optional VBT tests in the intended licensed environment and perform the owner's final content/history review. Repository visibility is a separate decision from passing tests.
