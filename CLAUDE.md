# Kànjiàn: notes for Claude

Read README.md first. Run `make check` after every change.

## Writing about a work: always check it against sources

Every time you write or change a work's introduction, "Look closer" notes or
"What critics and historians say" (the `editorial` block in `data/works/*.json`),
follow these steps. `make collection` fails if a statement has no source.

1. **Gather sources before writing.** Start with the work's own museum record
   (`record.url`), including its inscriptions, colophons and technique tabs, and the
   museum text already in the file. Then find more reliable sources, in this order:
   - museum essays and exhibition pages (theme.npm.edu.tw, metmuseum.org, clevelandart.org);
   - inscriptions and colophons on the work, as transcribed or translated by the museum;
   - scholarship by named art historians (books, journal articles, university pages);
   - encyclopedias (Wikipedia, Britannica) last; prefer the scholarship they cite.

   Read each page yourself. A search-result summary is not a source.
2. **Write only what a source says.** Every sentence gets `sources`: keys from the
   work's `editorial.sources`, or the built-ins `museum` (the work's record) and
   `image` (only for something plainly visible in the image on the page).
3. **Check each sentence against its sources.** Take each statement and confirm the
   cited page really says it: names, dates, numbers, attributions. If no source
   supports a claim, cut it or rewrite it to what the source does say. Do not
   "fill in" from memory, including life dates, names or locations.
4. **Report disagreement.** If sources conflict (dates, attribution, authenticity),
   say so on the page and cite both. Do not quietly pick one.
5. **Historians' views must name someone.** Each view names a person (or, if that is
   all there is, an institution) and cites where the view is stated. Paraphrase modern
   scholars; quote them only briefly (a short phrase, in `quote`). Traditional
   critics, inscriptions and colophons can be quoted in full.
6. **Record the check.** Set `editorial.checked.on` to the date you checked. Keep
   `status: "ai_draft"` until a curator or scholar has reviewed the text.
7. **Say what could not be checked.** If a source page could not be read (blocked or
   rate-limited), do not cite it. Tell the user which claims were dropped because of
   that, rather than retrying with tricks.

## Other rules

- Never add Claude attribution lines to commits or pull requests.
- Images from the National Palace Museum, Taipei, come through its IIIF service; never
  automate its CAPTCHA download buttons. Nothing from the Palace Museum, Beijing, whose
  terms forbid reuse without written permission.
