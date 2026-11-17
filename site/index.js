(function () {
  var search = document.getElementById("search");
  var chips = Array.prototype.slice.call(document.querySelectorAll(".chip"));
  var cards = Array.prototype.slice.call(document.querySelectorAll(".card"));
  var count = document.getElementById("count");
  var empty = document.getElementById("empty");
  var activeTag = new URLSearchParams(location.search).get("tag") || "";

  function apply() {
    var q = search.value.trim().toLowerCase();
    var shown = 0;
    cards.forEach(function (card) {
      var okText = !q || card.dataset.search.indexOf(q) !== -1;
      var okTag = !activeTag || card.dataset.tags.split("|").indexOf(activeTag) !== -1;
      card.hidden = !(okText && okTag);
      if (!card.hidden) shown++;
    });
    chips.forEach(function (c) {
      c.setAttribute("aria-pressed", String(c.dataset.tag === activeTag));
    });
    count.textContent = shown + (shown === 1 ? " recipe" : " recipes");
    empty.hidden = shown !== 0;
  }

  chips.forEach(function (chip) {
    chip.addEventListener("click", function () {
      activeTag = activeTag === chip.dataset.tag ? "" : chip.dataset.tag;
      apply();
    });
  });
  search.addEventListener("input", apply);
  apply();
})();
