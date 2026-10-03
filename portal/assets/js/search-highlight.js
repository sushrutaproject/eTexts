/* eTexts -- highlight search hits on a chapter page.
   Shared by every text: loaded by each text's _layouts/chapter.html from
   <collection root>/assets/js/search-highlight.js.

   When a chapter is opened from a search result (?q=…&mode=…&fold=1&parts=…),
   highlight the matches and jump to the first one the reader can see.
   `parts` limits highlighting to the registers that were searched:
   m = mūla (div.mula), c = commentaries (the other top-level divs),
   n = notes (section.notes). Absent = everything.
   Only matches within a single text node are found: a match spanning a
   verse-number span or a note reference won't highlight. */
(function () {
  "use strict";

  var params = new URLSearchParams(window.location.search);
  var q = params.get("q");
  if (!q) return;
  var mode = params.get("mode") === "regex" ? "regex" : "plain";
  var fold = params.get("fold") === "1";
  var parts = params.get("parts") || "mcn";

  var PART_NAME = { m: "mūla", c: "commentaries", n: "notes" };

  // Folding is length-preserving (every accented character in these texts
  // folds to exactly one plain one), so a match found in the folded string
  // can be sliced straight out of the original node text.
  var foldCache = {};
  function foldChar(c) {
    if (foldCache[c] !== undefined) return foldCache[c];
    var f = c.normalize("NFD").replace(/[̀-ͯ]/g, "");
    if (f.length !== 1) f = c;
    foldCache[c] = f;
    return f;
  }
  function foldText(s) {
    var out = "";
    var plainFrom = 0;
    for (var i = 0; i < s.length; i++) {
      if (s.charCodeAt(i) < 128) continue;
      out += s.slice(plainFrom, i) + foldChar(s[i]);
      plainFrom = i + 1;
    }
    return plainFrom === 0 ? s : out + s.slice(plainFrom);
  }

  function regions(root) {
    if (parts.indexOf("m") >= 0 && parts.indexOf("c") >= 0 && parts.indexOf("n") >= 0) return [root];
    var sel = [];
    if (parts.indexOf("m") >= 0) sel.push(":scope > div.mula");
    if (parts.indexOf("c") >= 0) sel.push(":scope > div:not(.mula)");
    if (parts.indexOf("n") >= 0) sel.push(":scope > section.notes li");
    return sel.length ? Array.prototype.slice.call(root.querySelectorAll(sel.join(", "))) : [];
  }

  function highlight() {
    try {
      var source = (mode === "regex") ? q : q.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
      if (fold) source = foldText(source);
      var re;
      try { re = new RegExp(source, "gi"); } catch (e) { return; }

      var root = document.querySelector(".chapter-text");
      if (!root) return;

      // Collect text nodes first; we mutate the DOM afterwards.
      var nodes = [];
      regions(root).forEach(function (el) {
        var walker = document.createTreeWalker(el, NodeFilter.SHOW_TEXT, null, false);
        var n;
        while ((n = walker.nextNode())) nodes.push(n);
      });

      var marks = [];
      nodes.forEach(function (node) {
        var text = node.nodeValue;
        var haystack = fold ? foldText(text) : text;
        re.lastIndex = 0;
        if (!re.test(haystack)) return;
        re.lastIndex = 0;

        var frag = document.createDocumentFragment();
        var last = 0, m, guard = 0;
        while ((m = re.exec(haystack)) !== null) {
          if (m.index === re.lastIndex) re.lastIndex++;
          if (m[0].length === 0) continue;
          if (++guard > 1000) break;
          if (m.index > last) frag.appendChild(document.createTextNode(text.slice(last, m.index)));
          var mark = document.createElement("mark");
          mark.className = "search-hit";
          mark.textContent = text.slice(m.index, m.index + m[0].length);  // real spelling
          frag.appendChild(mark);
          marks.push(mark);
          last = m.index + m[0].length;
        }
        if (last < text.length) frag.appendChild(document.createTextNode(text.slice(last)));
        node.parentNode.replaceChild(frag, node);
      });
      if (!marks.length) return;

      // Hits inside a commentary the reader has switched off are not visible.
      var visible = marks.filter(function (mk) { return mk.getClientRects().length > 0; });
      var hidden = marks.length - visible.length;
      if (visible.length) visible[0].scrollIntoView({ block: "center" });

      var where = "";
      if (parts !== "mcn") {
        var names = parts.split("").map(function (p) { return PART_NAME[p]; });
        where = " (" + (names.length === 1 ? names[0] + " only" : names.join(" and ")) + ")";
      }
      var banner = document.createElement("p");
      banner.className = "search-banner";
      banner.innerHTML = marks.length + (marks.length === 1 ? " match" : " matches") +
        " for <strong></strong> in this chapter" + where + ". " +
        (hidden ? hidden + " of them " + (hidden === 1 ? "is" : "are") +
                  " in a commentary that is switched off above. " : "") +
        '<a href="' + window.location.pathname + '">Clear highlighting</a>';
      banner.querySelector("strong").textContent = q;
      var header = document.querySelector(".chapter-header");
      if (header) header.appendChild(banner);
    } catch (err) {
      /* Highlighting is a convenience; never let it break the page. */
    }
  }

  // Wait until the page's own scripts (the show/hide-commentary switches)
  // have run, so we know which hits are visible.
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", highlight);
  } else {
    highlight();
  }
})();
