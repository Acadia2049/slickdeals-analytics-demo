# One-minute project walkthrough

**0–15 seconds — What the tool does.** “This is a reproducible analytics system for timestamped public-web observations. I built the collection and evidence checks, the transformations and metric contracts, and this read-only dashboard.”

**15–30 seconds — Show the interface.** Open Merchant Overview, select Amazon and November 10–16 in the observed-data dashboard. Point to the sample counts next to the metrics. Explain that snapshot share is observed Frontpage composition, not market share or sales.

**30–45 seconds — Trace one result.** Point to Comment Velocity, `0.205042`. It gives each Deal equal weight, retains negative changes, and uses counter-specific observation hours. Open the metric walkthrough rather than claiming the raw ratio is the metric.

**45–60 seconds — Show an observation.** Open Deal Explorer and search `20255670`. Inspect the November 10 06:31:45 UTC row: comments changed from 17 to 16. Point to the plain-language comparison explanation and source-check result. Close by explaining how similar event-level checks would help a study detect missing or duplicated suggestion logs.

For a credential-free demonstration, use the synthetic store and explicitly say its values are fictional. Its metrics intentionally differ from the observed-data screenshots. Do not present synthetic fixture validation as field-experiment results.
