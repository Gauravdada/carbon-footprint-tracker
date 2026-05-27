/*
  calculate.js
  ─────────────────────────────────────────────────────────────
  Live CO2 meter for the calculate form.
  Reads emission factors from each input's `data-factor` attribute.
  Updates the meter display on every keystroke (no page reload).

  Data flow:
    User types → updateMeter() → reads all .co2-input values
    → multiplies by data-factor → sums → updates DOM display
  ─────────────────────────────────────────────────────────────
*/

document.addEventListener('DOMContentLoaded', function () {

  // All inputs that have a data-factor attribute
  const inputs = document.querySelectorAll('.co2-input');

  // DOM elements to update
  const liveCo2Display  = document.getElementById('liveCo2');
  const familyCo2Display = document.getElementById('familyCo2');
  const meterBar        = document.getElementById('meterBar');
  const meterLabel      = document.getElementById('meterLabel');

  // FAMILY_SIZE is injected from Flask in calculate.html:
  //   <script>const FAMILY_SIZE = {{ user.family_size }};</script>
  const familySize = typeof FAMILY_SIZE !== 'undefined' ? FAMILY_SIZE : 1;

  // City daily target in kg (1.8 tonnes/year = ~4.93 kg/day)
  const DAILY_TARGET_KG = (1.8 * 1000) / 365;

  // ── Main update function ─────────────────────────────────
  function updateMeter() {
    let total = 0;

    inputs.forEach(function (input) {
      const value  = parseFloat(input.value) || 0;
      const factor = parseFloat(input.getAttribute('data-factor')) || 0;
      total += value * factor;
    });

    total = Math.max(0, total);

    // Update numeric display
    liveCo2Display.textContent  = total.toFixed(2);
    familyCo2Display.textContent = (total * familySize).toFixed(2);

    // Update progress bar (caps at 100%)
    const pct = Math.min((total / DAILY_TARGET_KG) * 100, 100);
    meterBar.style.width = pct + '%';

    // Change bar color and label based on level
    meterBar.classList.remove('low', 'medium', 'high');
    if (total === 0) {
      meterLabel.textContent = 'Enter your activities above.';
    } else if (pct < 50) {
      meterBar.classList.add('low');
      meterLabel.textContent = `✅ Great! You're below the city average.`;
    } else if (pct < 100) {
      meterBar.classList.add('medium');
      meterLabel.textContent = `⚠️ Approaching the daily city target.`;
    } else {
      meterBar.classList.add('high');
      meterLabel.textContent = `🚨 Above the daily target — check the tips after you save.`;
    }
  }

  // ── Attach event listeners ───────────────────────────────
  inputs.forEach(function (input) {
    input.addEventListener('input', updateMeter);
    input.addEventListener('change', updateMeter);
  });

  // Run once on page load
  updateMeter();

});
