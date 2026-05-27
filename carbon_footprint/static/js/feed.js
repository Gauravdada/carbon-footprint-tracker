/*
  feed.js
  ─────────────────────────────────────────────────────────────
  JavaScript for the InShorts-style card feeds.
  Uses the IntersectionObserver API to trigger card animations
  as the user scrolls — no dependencies required.
  ─────────────────────────────────────────────────────────────
*/

document.addEventListener('DOMContentLoaded', function () {

  const cards = document.querySelectorAll('.feed-card');

  /*
   * IntersectionObserver fires a callback when an element
   * enters or exits the viewport.
   * threshold: 0.15 means 15% of the card must be visible.
   */
  const observer = new IntersectionObserver(function (entries) {
    entries.forEach(function (entry) {
      if (entry.isIntersecting) {
        // Card has entered the viewport — trigger slide-up animation
        entry.target.style.animationPlayState = 'running';
        observer.unobserve(entry.target); // Only animate once
      }
    });
  }, { threshold: 0.15 });

  // Pause all animations initially; let observer control them
  cards.forEach(function (card) {
    card.style.animationPlayState = 'paused';
    observer.observe(card);
  });

});
