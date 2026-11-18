// 企画ページの描画。晴菜さんの programs.js（2026-11-17）から、確認用の企画選択欄を外し、
// 中身を ../assets/kikaku.js（トップのカードと共通）から読む形にしたもの。
(() => {
  const list = window.KIKAKU || [];
  const programs = Object.fromEntries(list.map(p => [p.id, p]));
  const PART = window.KIKAKU_PART || {};
  const page = document.getElementById("festival-page");
  const IMG = id => "../assets/img/kikaku/" + id + ".webp";

  function text(id, value) { document.getElementById(id).textContent = value; }
  function lines(id, values, tag) {
    const node = document.getElementById(id);
    node.replaceChildren();
    values.forEach((value, index) => {
      if (index) node.append(document.createElement(tag));
      node.append(document.createTextNode(value));
    });
  }

  function render(key) {
    if (!programs[key]) key = list[0].id;
    const program = programs[key];
    page.className = program.theme;
    page.style.setProperty("--image-position", program.position);
    document.title = program.name + "｜鳴門文化祭";
    text("breadcrumb-title", program.name);
    text("program-english", program.english);
    text("program-tag", PART[program.part] || "");
    lines("program-title", program.title, "wbr");
    lines("program-catch", program.catch, "br");
    text("about-heading", program.heading);
    text("program-description", program.description);
    text("coming-description", program.pending);
    text("coming-status", program.status);
    const image = document.getElementById("program-image");
    image.src = IMG(key);
    image.alt = program.alt;

    const caution = document.getElementById("program-caution");
    caution.hidden = !program.caution;
    if (program.caution) lines("program-caution-text", program.caution, "br");

    const information = document.getElementById("program-information");
    information.replaceChildren();
    for (const name of program.rows) {
      const row = document.createElement("div");
      const term = document.createElement("dt");
      const value = document.createElement("dd");
      term.textContent = name;
      const confirmed = program.information?.[name];
      value.className = confirmed ? "" : "pending";
      value.textContent = confirmed || "順次公開";
      row.append(term, value);
      information.append(row);
    }

    // ほかの企画：一覧の並びで、この企画の次から3つ
    const related = document.getElementById("related-list");
    related.replaceChildren();
    const keys = list.map(p => p.id);
    const index = keys.indexOf(key);
    const ordered = [...keys.slice(index + 1), ...keys.slice(0, index)].slice(0, 3);
    for (const candidate of ordered) {
      const item = programs[candidate];
      const link = document.createElement("a");
      link.className = "related";
      link.href = "?program=" + candidate;
      const picture = document.createElement("img");
      picture.src = IMG(candidate);
      picture.alt = "";
      picture.width = 95;
      picture.height = 76;
      picture.loading = "lazy";
      const label = document.createElement("div");
      const tag = document.createElement("small");
      tag.textContent = PART[item.part] || "";
      const title = document.createElement("strong");
      title.textContent = item.name;
      const arrow = document.createElement("span");
      arrow.textContent = "→";
      arrow.setAttribute("aria-hidden", "true");
      label.append(tag, title);
      link.append(picture, label, arrow);
      related.append(link);
    }
  }

  render(new URLSearchParams(location.search).get("program"));
})();
