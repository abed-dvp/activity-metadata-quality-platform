# Address–coordinate consistency diagnostic

This stage compares London catalog coordinates with geocoded addresses using a deterministic 30-row sample (seed 20261008).

Decision bands: <=500m consistent, 500–1500m uncertain, >1500m suspicious, no result unresolved. These are diagnostic thresholds, not verified ground truth. A mismatch can be due to entrance differences or ambiguous geocoding.

The OpenStreetMap Nominatim public endpoint must be used sparingly, with one thread, at most one request per second, clear User-Agent and cached results. Attribution: © OpenStreetMap contributors (ODbL). See https://operations.osmfoundation.org/policies/nominatim/

The workflow is explicitly triggered once via a committed trigger file; outputs are committed to reports/location/semantic. Production routing stays disabled.
