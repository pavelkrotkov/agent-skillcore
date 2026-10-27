# Floor-plane reconstruction and interpretation

## Geometry and evidence

Use original full-court footage. A moving crop removes camera context and can hide displacement. Define an explicit court convention, for example x from one baseline (0) to the other (18 m), y from one sideline (0) to the other (9 m); net x=9, attack lines x=6 and x=12. State which side the target occupies and preserve that orientation across samples. Verify the visible markings and competition's court dimensions rather than confusing basketball lines with volleyball lines.

For each stable camera segment, collect at least four non-collinear, well-spread floor intersections paired with known court coordinates. Prefer additional controls and independent holdouts spanning the area of interest. A four-point fit's training residual is not validation. Camera cuts, pan, zoom and stabilization changes require separate calibration or per-frame geometry. Wide-angle/panoramic footage may violate a single homography: inspect residuals spatially, use a justified local calibration or distortion model and widen uncertainty where unsupported. Do not report precise meters from a visually plausible overlay alone.

The supplied helper fits a least-squares projective mapping without external Python libraries:

```sh
python3 scripts/floor_map.py calibration.json > calibration-result.json
```

Paths above are relative to this skill directory. JSON contract:

```json
{
  "controls": [
    {"image": [0, 0], "court": [0, 0]},
    {"image": [900, 0], "court": [18, 0]},
    {"image": [900, 450], "court": [18, 9]},
    {"image": [0, 450], "court": [0, 9]}
  ],
  "holdouts": [{"image": [450, 225], "court": [9, 4.5]}],
  "points": [{"id": "set-feet", "kind": "floor", "image": [300, 300]}]
}
```

These synthetic coordinates demonstrate syntax, not a reusable calibration. Output reports each holdout's error in meters, RMS/max error and projected points. The helper does not choose acceptable residual thresholds, certify a camera, estimate measurement uncertainty or reject extrapolation. Inspect holdout errors and source geometry before using its coordinates. Its normalized least-squares solver still has finite numerical limits; a singular/ill-conditioned error requires better landmarks, not fabricated output. `kind` must be `floor`: this is a semantic guard, not proof the submitted pixel is grounded.

## Event reconstruction

Read native frames before and after each event. Record source evidence and a time/window for:

1. Setter's contact (or explicitly a prior non-setting team contact) and target's visible ground position then.
2. Subsequent approach and retreat anchors, including steps begun before the set when the recording permits.
3. Last grounded foot/feet region before takeoff; distinguish the final step from inferred takeoff time.
4. Attacker's ball contact time. Do not map the raised hand/head/ball pixel onto the floor to invent a hit location. Last-ground reference stays labeled while airborne; true airborne horizontal position needs an explicitly justified additional model.
5. First opposing contact or first floor landing, only if visible and temporally identified. A later bounce, teammate touch, defender's feet or post-cut position cannot establish it. Use a broad receiver floor zone when appropriate, labeled as a proxy, or null if unresolved.

Document occlusion, point-picking tolerance, timing window, calibration residuals and extrapolation. Perturb anchors by plausible pixel error to assess sensitivity. Report practical uncertainty ranges as estimates, not statistical confidence intervals. Round display precision accordingly. Interpolation between observed floor anchors is for visualization, not additional measurement; don't present held last-ground references as current motion.

## Runway hypothesis

Compute set-time to final-ground straight displacement and sparse observed ground-path length separately. Neither is the entire available runway: the approach may start before the set, include a retreat, or have missing anchors. Do not derive accurate speed from sparse/uncertain positions. Compare within matched camera/approach/set/action situations and include counterexamples. Short distance can support a descriptive pattern but cannot alone establish that it causes a high ball arc, cross-body swing or failed kill. Single-view floor mapping also cannot measure hand-ball spacing in 3D. State what the evidence supports, what would refute it and what another view would resolve.
