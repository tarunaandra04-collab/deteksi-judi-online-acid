// ringkas.js -- mengubah hasil server menjadi ringkasan sederhana untuk pengguna awam (dipakai popup dan lencana).
(() => {
  const META = {
    aman:    { word: "AMAN",      sentence: "Tidak ada tanda judi di halaman ini.",           color: "#15803d", lamp: 0 },
    waspada: { word: "HATI-HATI", sentence: "Ada tanda yang mencurigakan, tetapi belum pasti.", color: "#b45309", lamp: 1 },
    judi:    { word: "ADA JUDI",  sentence: "Halaman ini berisi konten judi online.",         color: "#dc2626", lamp: 2 },
  };

  // rec = {result (dari server), client ({strong, weak}: kata judi yang tampak)}
  function summarize(rec) {
    const r = rec.result;
    const label = META[r.label] ? r.label : "aman";
    const lvl = label === "judi" ? 2 : label === "waspada" ? 1 : 0;
    const c = rec.client || { strong: [], weak: [] };
    // pada halaman aman hanya kata kuat yang dihitung (kata ambigu seperti "jackpot" wajar muncul)
    const visible = label === "aman" ? (c.strong || []).length : (c.strong || []).length + (c.weak || []).length;
    const hidden = (r.evidence.hidden || []).length;
    const links = (r.evidence.judi_links || []).length;
    const rows = [
      { name: "Tulisan judi terlihat", n: visible, unit: "kata" },
      { name: "Tulisan judi tersembunyi", n: hidden, unit: "bagian" },
      { name: "Tautan ke situs judi", n: links, unit: "tautan" },
    ].map((x) => ({ ...x, level: x.n > 0 ? lvl : 0, text: x.n > 0 ? `${x.n} ${x.unit}` : "Tidak ada" }));
    // model menilai judi tanpa bukti kata kunci (judi yang tersamar): jelaskan agar tidak membingungkan
    if (lvl > 0 && rows.every((x) => x.n === 0)) rows.push({ name: "Pola isi halaman", n: 1, level: lvl, text: "Mirip halaman judi" });
    return { label, ...META[label], lvl, rows };
  }

  function reportText(rec) {
    const r = rec.result;
    const lines = [
      "LAPORAN DETEKSI KONTEN JUDI ONLINE",
      `Halaman : ${rec.url}`,
      `Waktu   : ${new Date(rec.at).toLocaleString("id-ID")}`,
      `Hasil   : ${META[r.label] ? META[r.label].word : r.label} (peluang judi ${(r.ml.p_judi * 100).toFixed(1)}%, model ${r.ml.model}, ambang ${r.ml.threshold})`,
      "", "Alasan:", ...r.reasons.map((x) => " - " + x),
    ];
    const kw = Object.entries(r.evidence.keywords_strong || {}).map(([k, v]) => `${k} x${v}`).join(", ");
    if (kw) lines.push("", "Kata kunci kuat: " + kw);
    if ((r.evidence.hidden || []).length) {
      lines.push("", "Teks tersembunyi:");
      r.evidence.hidden.forEach((x) => lines.push(` - <${x.tag}> ${x.reason}: "${x.snippet}"`));
    }
    if ((r.evidence.judi_links || []).length) lines.push("", "Tautan ke situs bernama judi: " + r.evidence.judi_links.join(", "));
    lines.push("", "Catatan: ini hasil prediksi komputer (prototipe skripsi), bukan keputusan akhir. Mohon verifikasi manual.");
    return lines.join("\n");
  }

  self.DJOSUM = { META, summarize, reportText };
})();
