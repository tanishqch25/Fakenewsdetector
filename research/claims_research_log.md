# Claims dataset research log

Generated 2026-10-29 by `research/write_research_log.py` from the pipeline's own artifacts.
No entry in this log was written by hand from memory.

## Pipeline

```
harvest_candidates.py -> candidates.tsv          (URLs discovered from RSS feeds and listings)
fetch_articles.py     -> logs/*.tsv + OS-temp cache   (HTTP status, served title, date, extracted text)
split_batches.py      -> cache/batch_NN.json     (usable articles grouped for review)
manual review         -> batches/batch_NN.json   (records + provenance, or an exclusion reason)
build_dataset.py      -> claims.json + rejected.tsv   (gates every record against the cached text)
validate_claims.py    -> schema, dedup and fetch-record checks
```

The article text used for verification is cached in the OS temp directory, outside the
repository, so no copied article prose is committed to the project.

## Funnel

| stage | count |
| --- | --- |
| candidate URLs harvested | 701 |
| distinct URLs fetched | 701 |
| fetched with HTTP 200 and >400 chars of text | 701 |
| articles handed to a reviewer | 693 |
| reviewer exclusions | 96 |
| records drafted by reviewers | 102 |
| records rejected by the merge gate | 0 |
| new records shipped | 102 |
| pre-existing records (untouched) | 12 |
| **total records in claims.json** | **114** |

## Sources

| organisation | harvested | fetched OK | reviewed | shipped |
| --- | --- | --- | --- | --- |
| Alt News | 140 | 140 | 140 | 51 |
| Factly | 140 | 140 | 140 | 0 |
| Newschecker | 120 | 120 | 120 | 27 |
| Vishvas News | 120 | 120 | 120 | 0 |
| BOOM | 105 | 105 | 105 | 0 |
| FactCheck.org | 40 | 40 | 40 | 0 |
| India Today Fact Check | 18 | 18 | 18 | 16 |
| The Quint WebQoof | 10 | 10 | 10 | 8 |
| Alt News (listing) | 8 | 8 | 0 | 0 |

## Status breakdown (shipped records)

| status | new | pre-existing | total |
| --- | --- | --- | --- |
| `false` | 70 | 8 | 78 |
| `misleading` | 31 | 2 | 33 |
| `verified` | 1 | 1 | 2 |
| `unverified` | 0 | 1 | 1 |

## Category breakdown (shipped records)

| category | new | total |
| --- | --- | --- |
| `politics` | 45 | 49 |
| `ai-media` | 16 | 16 |
| `communal` | 13 | 13 |
| `world` | 9 | 11 |
| `society` | 5 | 6 |
| `environment` | 4 | 5 |
| `crime` | 4 | 4 |
| `religion` | 1 | 3 |
| `scam` | 3 | 3 |
| `health` | 1 | 2 |
| `finance` | 0 | 1 |
| `elections` | 1 | 1 |

## Every shipped record

Verification status legend:

- **verified-quote** - the record passed the merge gate, meaning a verbatim conclusion
  quote from the article was found inside the locally cached article text, the article was
  fetched with HTTP 200, and more than 400 characters of body text were extracted.
- **legacy** - a record that was already in `claims.json` before this expansion. AFP and
  Reuters return HTTP 401/403 to automated fetchers, so their articles could not be
  re-verified by this pipeline and are marked as such rather than claimed as verified.

| id | status | category | fact-checker | evidence URL | verification |
| --- | --- | --- | --- | --- | --- |
| `us-voting-machines-old-clips-2026` | false | politics | AFP Fact Check | https://factcheck.afp.com/doc.afp.com.D49L6T3 | legacy - not re-fetchable |
| `voting-machine-glitches-systemic-fraud` | misleading | politics | AFP Fact Check | https://factcheck.afp.com/doc.afp.com.D46B69E | legacy - not re-fetchable |
| `eiffel-tower-palestinian-flag-ai` | false | world | AFP Fact Check | https://factcheck.afp.com/doc.afp.com.D42U963 | legacy - not re-fetchable |
| `eiffel-tower-fire-ai-clip` | false | world | AFP Fact Check | https://factcheck.afp.com/doc.afp.com.D3WQ8KE | legacy - not re-fetchable |
| `bengal-post-poll-old-video-2026` | false | politics | Alt News | https://www.altnews.in/congress-and-tmc-leaders-are-sharing-an-old-video-depicting-violence-following-the-west-bengal-election-results/ | legacy - not re-fetchable |
| `bangladesh-scripted-marriage-video` | false | society | BOOM | https://www.boomlive.in/fact-check/scripted-video-from-bangladesh-viral-with-false-forced-marriage-claim-32337 | legacy - not re-fetchable |
| `sitharaman-2023-presser-clip` | false | politics | Factly | https://factly.in/a-video-of-nirmala-sitharaman-from-2023-is-falsely-shared-as-a-clip-from-a-recent-press-conference/ | legacy - not re-fetchable |
| `irs-refund-up-11-percent` | verified | finance | PolitiFact | https://politifact.com/factchecks/2026/may/11/nicholas-langworthy/tax-refunds-11-percent-reduction-irs/ | legacy - not re-fetchable |
| `5g-health-harm-claim` | false | health | World Health Organization / ICNIRP (institutional review) | https://www.who.int/health-topics/radiation | legacy - not re-fetchable |
| `climate-petition-consensus-claim` | misleading | environment | NASA Science (institutional consensus record) | https://climate.nasa.gov/scientific-consensus/ | legacy - not re-fetchable |
| `pope-puffer-coat-ai-image` | false | religion | Reuters Fact Check | https://www.reuters.com/article/fact-check/image-of-pope-francis-wearing-oversized-white-puffer-coat-is-ai-generated-idUSL1N36120G/ | legacy - not re-fetchable |
| `christchurch-conversions-350` | unverified | religion | Alt News (media provenance only; figure itself unverified) | https://www.altnews.in/old-video-and-images-shared-as-individuals-converting-to-islam-after-christchurch-massacre/ | legacy - not re-fetchable |
| `neha-bora-luxury-car-belongs-to-lawyer` | false | politics | Alt News | https://www.altnews.in/did-neha-bora-go-to-mandir-marg-police-station-in-her-luxury-car-no-the-vehicle-belongs-to-her-lawyer/ | verified-quote |
| `bengal-left-bookstalls-only-hindu-festivals-claim` | false | politics | Alt News | https://www.altnews.in/do-left-parties-in-bengal-set-up-bookstalls-during-christmas-and-eid-yes-they-do/ | verified-quote |
| `neha-bora-bangladesh-uprising-clip-out-of-context` | misleading | politics | Alt News | https://www.altnews.in/no-neha-bora-did-not-call-for-bangladesh-like-situation-in-india-viral-claim-misses-important-context/ | verified-quote |
| `cjp-forged-bail-bond-document` | false | politics | Alt News | https://www.altnews.in/ai-generated-image-of-a-bond-with-dipkes-signature-is-being-falsely-shared-bu-bjp-leader/ | verified-quote |
| `college-dance-clips-falsely-linked-cjp-protests` | false | politics | Alt News | https://www.altnews.in/college-dance-performance-videos-falsely-linked-to-cjp-protests-against-gyanesh-kumar/ | verified-quote |
| `varanasi-police-ai-generated-dance-video-claim` | false | ai-media | Alt News | https://www.altnews.in/varanasi-police-falsely-claims-viral-video-of-cops-recording-dancers-is-ai-generated/ | verified-quote |
| `bengal-sir-seven-lakh-appeals-claim` | false | elections | Alt News | https://www.altnews.in/only-7-lakh-deleted-voters-appealed-in-bengal-sir-tribunals-suvendu-adhiakris-claim-false-shows-ec-data/ | verified-quote |
| `gwalior-snatcher-falsely-called-muslim` | false | communal | Alt News | https://www.altnews.in/gwalior-mobile-snatcher-falsely-portrayed-as-muslim-man-posing-as-hindu-in-viral-posts/ | verified-quote |
| `puffed-rice-vendor-assault-scripted-skit` | false | society | Alt News | https://www.altnews.in/viral-video-of-poor-puffed-rice-vendor-being-assaulted-is-a-scripted-skit/ | verified-quote |
| `bail-release-threat-video-actually-from-june` | misleading | politics | Alt News | https://www.altnews.in/viral-video-of-swatantra-bhardwaj-threatening-bhim-army-chief-predates-his-september-17-release-on-interim-bail/ | verified-quote |
| `kharge-breakfast-table-morphed-photo` | false | politics | Alt News | https://www.altnews.in/mallikarjun-kharge-kept-away-from-rahul-gandhi-anwar-ibrahims-breakfast-table-morphed-photo-viral/ | verified-quote |
| `modi-xi-jinping-portrait-old-video-2019` | false | politics | Alt News | https://www.altnews.in/modi-gifted-self-portrait-to-xi-jinping-no-old-video-falsely-viral/ | verified-quote |
| `fake-gaurav-bhatia-quote-graphic-2026` | false | politics | Alt News | https://www.altnews.in/saurav-das-shares-fake-gaurav-bhatia-quote-on-swatantra-bhardwaj-deletes-after-being-called-out/ | verified-quote |
| `nepal-flood-alaska-glacier-burst-video` | false | environment | Alt News | https://www.altnews.in/glacier-burst-video-from-alaska-falsely-viral-as-nepal-flash-flood-trigger/ | verified-quote |
| `nepal-flood-shaligram-statue-man-made` | misleading | religion | Alt News | https://www.altnews.in/17-crore-year-old-shaligram-found-in-nepal-after-floods-man-made-idol-visuals-shared-with-misleading-claims/ | verified-quote |
| `bangladesh-street-assault-false-communal-angle` | misleading | communal | Alt News | https://www.altnews.in/assault-on-bangladeshi-muslim-woman-falsely-communalised-on-social-media/ | verified-quote |
| `nepal-floods-unrelated-old-and-ai-videos` | false | environment | Alt News | https://www.altnews.in/nepal-floods-unrelated-videos-of-past-disasters-ai-visuals-falsely-viral/ | verified-quote |
| `rajasthan-cjp-vehicles-self-damage-claim` | false | politics | Alt News | https://www.altnews.in/did-cjp-workers-in-rajasthan-break-their-own-car-windows-video-evidence-proves-this-claim-false/ | verified-quote |
| `bangladesh-family-murder-no-communal-angle` | false | communal | Alt News | https://www.altnews.in/no-communal-angle-in-murder-of-four-of-hindu-family-in-bangladesh-social-media-claims-false/ | verified-quote |
| `india-japan-50-million-hindus-settlement-contract` | false | politics | Alt News | https://www.altnews.in/no-japan-and-india-did-not-sign-a-contract-allowing-50-million-hindus-to-settle-in-japan/ | verified-quote |
| `cjp-ranka-companion-misidentified-as-protester` | false | politics | Alt News | https://www.altnews.in/no-man-seen-with-ashutosh-ranka-in-rajasthan-is-not-the-one-who-threatened-nepal-like-violence-at-jantar-mantar/ | verified-quote |
| `abhijeet-dipke-fake-jharkhand-resignation-quote` | false | politics | Alt News | https://www.altnews.in/not-seeking-jharkhand-cms-resignation-fake-quote-attributed-to-abhijeet-dipke-viral/ | verified-quote |
| `sonia-gandhi-1967-australian-go-go-dancers-photo` | false | politics | Alt News | https://www.altnews.in/1967-photo-of-australian-go-go-dancers-falsely-shared-to-attack-sonia-gandhi/ | verified-quote |
| `modi-national-anthem-doctored-video-siwan` | misleading | politics | Alt News | https://www.altnews.in/no-pm-modi-was-not-walking-around-as-national-anthem-played-viral-video-doctored/ | verified-quote |
| `arjun-singh-bjp-flag-independence-day-clipped-video` | misleading | politics | Alt News | https://www.altnews.in/bengal-minister-arjun-singh-hoisted-bjp-flag-on-independence-day-no-old-clipped-video-falsely-viral/ | verified-quote |
| `punjab-zombie-drug-video-staged-in-rajasthan` | false | society | Alt News | https://www.altnews.in/zombie-drugs-video-shared-by-harbhajan-singh-is-not-from-punjab/ | verified-quote |
| `fake-italian-embassy-statement-x-satire-account` | false | politics | Alt News | https://www.altnews.in/republic-gujarat-samachar-write-reports-based-on-fake-italian-embassy-statement/ | verified-quote |
| `jharkhand-police-protester-video-actually-patna-rally` | false | politics | Alt News | https://www.altnews.in/bjp-shares-patna-video-as-female-protester-roughed-up-by-jharkhand-police/ | verified-quote |
| `siwan-police-ak47-firing-claim` | false | politics | Alt News | https://www.altnews.in/bihar-siwan-opened-fire-by-police-on-student-protesters-cjp-bihar-band/ | verified-quote |
| `bengal-anti-goonda-act-not-yet-law` | false | politics | Alt News | https://www.altnews.in/the-law-bengal-cm-suvendu-adhikari-invoked-against-july-24-protesters-is-not-yet-law/ | verified-quote |
| `nadda-modi-staged-welcome-viral-video` | false | politics | Alt News | https://www.altnews.in/fact-check-viral-video-does-not-show-pm-modi-and-jp-nadda-arriving-together-or-staging-a-greeting-for-the-cameras/ | verified-quote |
| `delhi-jantar-mantar-pellet-gun-use` | verified | politics | Alt News | https://www.altnews.in/delhi-police-records-confirm-what-was-already-evident-pellet-guns-were-used-on-protestors-on-july-20/ | verified-quote |
| `delhi-dcp-resignation-deepfake-video` | false | ai-media | Alt News | https://www.altnews.in/delhi-dcp-resigned-to-support-students-protest-no-viral-video-is-a-deepfake/ | verified-quote |
| `mexico-world-cup-video-falsely-linked-delhi-protest` | misleading | politics | Alt News | https://www.altnews.in/mexico-world-cup-celebration-video-falsely-linked-to-delhi-cjp-protest/ | verified-quote |
| `ranchi-clash-video-falsely-shared-as-kolkata-protest` | misleading | politics | Alt News | https://www.altnews.in/bjp-members-pelting-stones-during-kolkata-cjp-protest-ranchi-video-falsely-viral/ | verified-quote |
| `naara-e-takbeer-clipped-video-cjp-protest` | misleading | communal | Alt News | https://www.altnews.in/bjp-leader-and-supporters-shared-clipped-video-of-naara-e-taqbeer-slogans-raised-at-cjp-protest-jantar-mantar/ | verified-quote |
| `piyush-goyal-hanging-remark-deepfake` | false | ai-media | Alt News | https://www.altnews.in/no-piyush-goyal-did-not-call-for-hanging-cockroaches-viral-video-is-a-deepfake/ | verified-quote |
| `jamaat-e-islami-fake-support-letter-cjp` | false | communal | Alt News | https://www.altnews.in/based-on-viral-fake-letter-republic-news-18-claim-jamaat-e-islami-support-to-cjp/ | verified-quote |
| `gaya-road-accident-video-falsely-shared-as-protest-arson` | misleading | communal | Alt News | https://www.altnews.in/mob-vandalizing-suv-bihar-video-falsely-viral-as-muslim-cjp-protestor-torching-bjp-leaders-car/ | verified-quote |
| `naseeruddin-shah-old-mumbai-video-jantar-mantar` | misleading | politics | Alt News | https://www.altnews.in/old-video-from-mumbai-falsely-circulated-as-naseeruddin-shah-joining-jantar-mantar-stir/ | verified-quote |
| `nail-baton-videos-july-20-delhi-protest-official-denial` | false | politics | Alt News | https://www.altnews.in/baton-with-nails-videos-indeed-from-july-20-protests-delhi-police-pibs-fact-check-incorrect/ | verified-quote |
| `cjp-protest-hydrogen-train-old-patna-video` | false | politics | Alt News | https://www.altnews.in/bjp-leaders-share-old-video-from-patna-claiming-cjp-protestors-pelted-stones-at-newly-launched-hydrogen-train/ | verified-quote |
| `sunita-williams-jantar-mantar-old-kerala-video` | false | politics | Alt News | https://www.altnews.in/no-sunita-williams-did-not-visit-cjp-protest-site-at-jantar-mantar/ | verified-quote |
| `baruipur-accused-fake-polling-agent-document` | false | politics | Alt News | https://www.altnews.in/baruipur-rape-murder-accused-ananda-sardar-was-cpims-polling-agent-no-fake-document-viral/ | verified-quote |
| `modi-auckland-speech-beef-claim` | false | politics | Alt News | https://www.altnews.in/no-pm-modi-did-not-say-india-was-worlds-largest-beef-producer/ | verified-quote |
| `rishikesh-sadhu-not-muslim-in-disguise` | false | communal | Alt News | https://www.altnews.in/rishikesh-muslim-man-wasnt-pretending-to-be-hindu-sadhu-approaching-girls/ | verified-quote |
| `modi-melbourne-event-ai-morphed-newspaper-clipping` | false | ai-media | Alt News | https://www.altnews.in/did-australian-media-expose-that-free-curry-and-roti-drew-crowds-to-modi-event-fact-check/ | verified-quote |
| `paris-old-psg-clashes-as-morocco-world-cup-riots` | false | world | Alt News | https://www.altnews.in/no-viral-video-does-not-show-migrant-moroccans-rioting-in-paris-after-world-cup-defeat/ | verified-quote |
| `kurukshetra-priest-attack-accused-not-muslim` | false | communal | Alt News | https://www.altnews.in/kurukshetra-video-accused-in-temple-priest-attack-not-muslims/ | verified-quote |
| `iskcon-mid-day-meal-vegetarian-state-protein-claim` | false | health | Alt News | https://www.altnews.in/eggs-off-the-plate-the-science-behind-the-mid-day-meal-debate/ | verified-quote |
| `pune-fort-murder-case-dance-video-misidentification` | false | crime | Alt News | https://www.altnews.in/viral-video-does-not-show-pune-fort-case-accused-siya-goyal-dancing/ | verified-quote |
| `diwali-offer-clone-shopping-apps-scam` | false | scam | India Today Fact Check | https://www.indiatoday.in/fact-check/story/fake-diwali-offers-clone-flipkart-meesho-apps-online-shopping-scams-3027023-2026-10-28 | verified-quote |
| `cyclone-arnab-old-unrelated-storm-videos` | misleading | environment | India Today Fact Check | https://www.indiatoday.in/fact-check/story/cyclone-arnab-fact-check-four-viral-storm-videos-old-unrelated-3026812-2026-10-28 | verified-quote |
| `ai-generated-bride-loco-pilot-video` | false | ai-media | India Today Fact Check | https://www.indiatoday.in/fact-check/story/ai-generated-bride-loco-pilot-viral-video-fact-check-3026260-2026-10-27 | verified-quote |
| `arunachal-china-faceoff-three-videos-false-claims` | misleading | politics | India Today Fact Check | https://www.indiatoday.in/fact-check/story/arunachal-india-china-face-offs-three-viral-videos-fact-check-3026160-2026-10-27 | verified-quote |
| `arunachal-china-border-two-videos-nathula-siang-protest` | misleading | politics | India Today Fact Check | https://www.indiatoday.in/fact-check/story/arunachal-pradesh-china-border-videos-unrelated-troop-tensions-fact-check-3025273-2026-10-26 | verified-quote |
| `chinese-army-arunachal-claim-bengaluru-mock-drill-video` | misleading | politics | India Today Fact Check | https://www.indiatoday.in/fact-check/story/fact-check-arunachal-pradesh-pla-viral-video-karnataka-mock-drill-3024782-2026-10-25 | verified-quote |
| `grok-2020-bengal-claim-delhi-protest-photo` | false | politics | India Today Fact Check | https://www.indiatoday.in/fact-check/story/grok-fact-check-saurav-das-delhi-protest-photo-not-2020-bengal-3017456-2026-10-14 | verified-quote |
| `delhi-protest-army-video-2017-pulwama-clip` | misleading | politics | India Today Fact Check | https://www.indiatoday.in/fact-check/story/indian-army-video-fact-check-2017-pulwama-clip-falsely-linked-to-delhi-protest-3016632-2026-10-13 | verified-quote |
| `abhijeet-dipke-fake-facebook-page` | false | scam | India Today Fact Check | https://www.indiatoday.in/fact-check/story/abhijeet-dipke-fake-facebook-account-blue-tick-page-delhi-protests-3016579-2026-10-13 | verified-quote |
| `philippines-diyandi-festival-video-as-delhi-protest` | misleading | politics | India Today Fact Check | https://www.indiatoday.in/fact-check/story/delhi-protest-video-fact-check-gyanesh-kumar-philippines-diyandi-festival-3015089-2026-10-11 | verified-quote |
| `jammu-rajput-rally-video-as-jantar-mantar-mob` | misleading | communal | India Today Fact Check | https://www.indiatoday.in/fact-check/story/jantar-mantar-protest-video-fact-check-jammu-rajput-rally-not-hindu-groups-3013394-2026-10-09 | verified-quote |
| `fake-fundraiser-ads-indian-pilot-hero` | false | scam | India Today Fact Check | https://www.indiatoday.in/fact-check/story/smit-machchhar-scam-fundraiser-warning-fake-donation-ads-hero-pilot-3012662-2026-10-08 | verified-quote |
| `messi-farewell-2022-world-cup-parade-video` | misleading | society | India Today Fact Check | https://www.indiatoday.in/fact-check/story/argentina-world-cup-victory-parade-video-fact-check-old-clip-shared-as-messi-farewell-3012254-2026-10-08 | verified-quote |
| `lapid-netanyahu-modi-playbook-deepfake-video` | false | ai-media | India Today Fact Check | https://www.indiatoday.in/fact-check/story/fact-check-yair-lapid-netanyahu-modi-playbook-video-deepfake-3011888-2026-10-07 | verified-quote |
| `gyanesh-kumar-protest-old-college-dance-clips` | misleading | politics | India Today Fact Check | https://www.indiatoday.in/fact-check/story/gyanesh-kumar-protest-videos-fact-check-chandigarh-college-dance-clips-old-delhi-election-commission-3011152-2026-10-06 | verified-quote |
| `virar-bangladeshi-flag-film-shoot-misidentified` | false | communal | India Today Fact Check | https://www.indiatoday.in/fact-check/story/virar-bangladeshi-flag-video-fact-check-film-shoot-not-illegal-migrants-3010032-2026-10-05 | verified-quote |
| `cyclone-arnab-visakhapatnam-old-typhoon-bavi-video` | false | environment | The Quint WebQoof | https://www.thequint.com/news/webqoof/old-video-from-us-territory-falsely-linked-to-cyclone-arnab-visakhapatnam-fact-check | verified-quote |
| `china-pla-captured-indian-soldier-old-video` | misleading | world | The Quint WebQoof | https://www.thequint.com/news/webqoof/old-video-chinese-army-captured-indian-soldier-fact-check | verified-quote |
| `israelis-singing-hanuman-chalisa-tel-aviv-ai-video` | false | ai-media | The Quint WebQoof | https://www.thequint.com/news/webqoof/viral-video-of-israelis-singing-hanuman-chalisa-in-tel-aviv-ai-generated-fact-check | verified-quote |
| `ai-image-rss-route-march-kannur-kerala` | false | ai-media | The Quint WebQoof | https://www.thequint.com/news/webqoof/ai-generated-image-falsely-shared-to-show-rss-march-in-keralas-kannur-fact-check | verified-quote |
| `ai-video-dgta-admitting-china-arunachal` | false | ai-media | The Quint WebQoof | https://www.thequint.com/news/webqoof/dgta-lt-gen-girish-kalia-did-not-admit-china-controlling-parts-of-arunachal-fact-check | verified-quote |
| `ai-image-sonia-gandhi-meeting-epstein` | false | ai-media | The Quint WebQoof | https://www.thequint.com/news/webqoof/image-of-sonia-gandhi-meeting-jeffrey-epstein-is-ai-altered-fact-check | verified-quote |
| `old-modi-meerut-speech-shared-as-anti-cec-reaction` | false | politics | The Quint WebQoof | https://www.thequint.com/news/webqoof/old-video-shared-as-recent-video-of-pm-modi-reacting-to-anti-cec-movement-fact-check | verified-quote |
| `ai-altered-us-senator-india-failed-state` | false | ai-media | The Quint WebQoof | https://www.thequint.com/news/webqoof/us-senator-called-india-a-failed-state-altered-video-fact-check | verified-quote |
| `scripted-bihar-video-man-marrying-daughter-dowry` | false | society | Newschecker | https://newschecker.in/fact-check/scripted-video-hindu-man-marrying-daughter-dowry/ | verified-quote |
| `madrid-street-vendors-video-as-france-looting` | misleading | world | Newschecker | https://newschecker.in/fact-check/does-this-video-show-protesters-hawking-luxury-products-looted-during-france-riot/ | verified-quote |
| `2015-mecca-execution-video-as-bangladeshi-nationals-2026` | misleading | world | Newschecker | https://newschecker.in/fact-check/old-video-falsely-shared-as-showing-execution-of-two-bangladeshi-nationals-in-saudi-arabia/ | verified-quote |
| `kaaba-couple-photo-as-executed-bangladeshi-nationals` | false | world | Newschecker | https://newschecker.in/fact-check/does-this-photo-show-bangladeshi-nationals-who-were-executed-in-saudi-arabia/ | verified-quote |
| `tbilisi-2024-protest-video-as-france-unrest` | misleading | world | Newschecker | https://newschecker.in/fact-check/old-video-from-georgia-falsely-linked-to-ongoing-protests-in-france/ | verified-quote |
| `ai-altered-pakistani-flag-rathee-london-protest` | false | ai-media | Newschecker | https://newschecker.in/fact-check/altered-photo-shared-to-show-pakistani-man-at-dhruv-rathees-london-protest-against-cec/ | verified-quote |
| `london-independence-day-flags-video-as-anti-cec-protest` | misleading | politics | Newschecker | https://newschecker.in/fact-check/old-video-pakistani-bangladeshi-flags-dhruv-rathee-anti-cec-protest-london/ | verified-quote |
| `bangladesh-shrine-vandalism-video-as-hindu-temple` | false | communal | Newschecker | https://newschecker.in/fact-check/does-this-video-show-a-temple-being-vandalised-in-bangladesh-amid-durga-puja/ | verified-quote |
| `ai-image-rahul-gandhi-kissing-student-activist` | false | ai-media | Newschecker | https://newschecker.in/fact-check/ai-generated-image-falsely-shows-rahul-gandhi-kissing-neha-bora/ | verified-quote |
| `patna-august-march-video-as-delhi-tiranga-march` | misleading | politics | Newschecker | https://newschecker.in/fact-check/old-video-from-patna-shared-as-tiranga-march-in-delhi-on-october-16/ | verified-quote |
| `modi-meerut-february-2026-video-as-anti-cec-reaction` | misleading | politics | Newschecker | https://newschecker.in/fact-check/anti-cec-stir-this-video-of-pm-modi-lashing-out-at-congress-is-old/ | verified-quote |
| `jharkhand-hc-2025-video-as-cji-surya-kant-exchange` | misleading | politics | Newschecker | https://newschecker.in/fact-check/old-video-from-jharkhand-hc-falsely-shared-as-heated-exchange-between-cji-and-sc-lawyer/ | verified-quote |
| `student-leader-cop-altercation-as-male-congress-worker-attack` | false | politics | Newschecker | https://newschecker.in/fact-check/male-congress-worker-attacking-woman-cop-anti-cec-protest-delhi/ | verified-quote |
| `assam-cm-old-video-cjp-protest-threat` | misleading | politics | Newschecker | https://newschecker.in/fact-check/will-kick-them-out-does-viral-video-show-assam-cm-threatening-cjp-protesters/ | verified-quote |
| `scripted-video-elderly-muslim-man-harassment` | false | communal | Newschecker | https://newschecker.in/fact-check/scripted-video-shared-as-showing-elderly-disabled-muslim-man-being-harassed-in-india/ | verified-quote |
| `tharoor-mecca-pact-altered-interview-audio` | false | ai-media | Newschecker | https://newschecker.in/fact-check/video-claiming-to-show-shashi-tharoor-calling-mecca-pact-a-threat-to-india-is-altered/ | verified-quote |
| `netanyahu-9-11-remark-clipped-un-speech` | misleading | world | Newschecker | https://newschecker.in/fact-check/did-benjamin-netanyahu-say-america-deserved-9-11-no-clipped-video-goes-viral/ | verified-quote |
| `jamui-case-girl-video-false-identity` | false | crime | Newschecker | https://newschecker.in/fact-check/jamui-molestation-case-no-this-video-does-not-show-survivor/ | verified-quote |
| `meloni-palestinian-flag-ai-generated-video` | false | ai-media | Newschecker | https://newschecker.in/fact-check/ai-generated-video-falsely-shows-giorgia-meloni-carrying-palestinian-flag-at-un-event/ | verified-quote |
| `jamui-case-police-parading-accused-videos` | false | crime | Newschecker | https://newschecker.in/fact-check/unrelated-videos-shared-as-police-parading-accused-in-jamui-molestation-case/ | verified-quote |
| `sushant-rajput-ai-generated-cctv-screengrab` | false | ai-media | Newschecker | https://newschecker.in/ai-deepfake/sushant-singh-rajput-death-case-ai-generated-image-falsely-shared-as-leaked-cctv-screengrab/ | verified-quote |
| `bihar-mla-old-clip-jamui-case-reaction` | misleading | politics | Newschecker | https://newschecker.in/fact-check/old-video-of-bjp-mla-maithili-thakur-shared-as-her-reaction-to-jamui-molestation-case/ | verified-quote |
| `patna-junction-vendor-harassment-scripted-video` | false | society | Newschecker | https://newschecker.in/fact-check/video-of-man-harassing-street-vendor-at-patna-junction-is-scripted/ | verified-quote |
| `kolkata-airport-mosque-bangladesh-video` | false | communal | Newschecker | https://newschecker.in/fact-check/video-from-bangladesh-shared-as-showing-136-yr-old-masjid-near-kolkata-airport-being-razed-to-make-way-for-temple/ | verified-quote |
| `tehran-irgc-fire-old-china-video` | false | world | Newschecker | https://newschecker.in/fact-check/old-video-shared-as-us-attack-on-irgc-facility-in-tehran/ | verified-quote |
| `russia-fire-video-actually-egypt` | false | world | Newschecker | https://newschecker.in/fact-check/old-video-from-egypt-falsely-linked-to-recent-ukrainian-drone-attack-on-russia/ | verified-quote |
| `gurugram-hit-and-run-rally-old-video` | false | crime | Newschecker | https://newschecker.in/fact-check/old-video-falsely-shared-as-car-rally-in-support-of-gurugram-hit-and-run-accused/ | verified-quote |

## Rejected by the merge gate

None. Every drafted record passed the gate.

## Excluded during review

96 fetched articles were reviewed and deliberately not turned into records.

| reason | count |
| --- | --- |
| not a fact-check | 16 |
| not a fact-check (straight news report) | 5 |
| roundup, not a single claim | 3 |
| duplicate of the existing claims.json entry eiffel-tower-palestinian-f | 2 |
| not a fact-check (straight news report of an alleged attack and FIR) | 1 |
| not a fact-check (straight news report of alleged assault and FIR) | 1 |
| not a fact-check (straight news report of a politician's statement) | 1 |
| not a fact-check; first-person account of graphic violence by a victim | 1 |
| not a fact-check; detainee testimonies of graphic violence | 1 |
| not a fact-check (news report aggregating international reactions) | 1 |
| not a fact-check: Alt News data-analysis report on Delhi SIR draft rol | 1 |
| not a fact-check: reported investigation into an alleged midnight depo | 1 |
| not a fact-check: news report on a party's election-expenditure disclo | 1 |
| not a fact-check: news report documenting attacks on Christian congreg | 1 |
| not a fact-check: news report on a politician's communal remark and th | 1 |
| not a fact-check: news report on a high court petition over a candidat | 1 |
| not a fact-check: news report on suspensions of independent journalist | 1 |
| not a fact-check: news report and commentary on a chief minister's byp | 1 |
| not a fact-check: news report on a killing and discrimination against  | 1 |
| not a fact-check: news report on the transfer of an IPS officer after  | 1 |
| not a fact-check: investigative feature on the background and associat | 1 |
| sensitive content: the fact-checked item is a sexualised AI-doctored c | 1 |
| not a fact-check: ground report on a murder case and an MLA's communal | 1 |
| not a fact-check: news report on a broadcast regulator's penalty order | 1 |
| not a fact-check: news feature on voter-roll deletions affecting a slu | 1 |
| not a fact-check: news report on a water supply disruption and residen | 1 |
| not a fact-check: follow-up impact story on a platform removing accoun | 1 |
| not a fact-check: investigative report identifying individuals in camp | 1 |
| not a fact-check: news roundup of recent incidents across several stat | 1 |
| not a fact-check: media criticism piece on how outlets labelled an acc | 1 |
| not a fact-check: news report on alleged police assault on two journal | 1 |
| not a fact-check: news feature on an arrest and a pending citizenship  | 1 |
| not a fact-check: analysis piece on a party's social media campaign | 1 |
| not a fact-check: media analysis/explainer on hostility toward TV repo | 1 |
| not a fact-check: investigative news report identifying who led the ne | 1 |
| not a fact-check: straight news report of the incident at the newspape | 1 |
| not a fact-check: straight news report of a disruption at a reading se | 1 |
| not a fact-check: profile/investigative report on a political appointe | 1 |
| not a fact-check: news report on platform restrictions of political pa | 1 |
| not a fact-check (investigative report on deleted X posts, no verdict  | 1 |
| not a fact-check (investigative report on a group's communally inflamm | 1 |
| not a fact-check (first-person account of the outlet's own post being  | 1 |
| not a fact-check (straight news report on party appointees deleting po | 1 |
| not a fact-check (human-interest profile of a private individual) | 1 |
| primarily sexualised digitally altered imagery of a named real person, | 1 |
| not a fact-check (straight news report of a fatal assault, with graphi | 1 |
| not a fact-check (reportage on platform censorship) | 1 |
| not a fact-check (RTI-based news report, no verdict sentence on a circ | 1 |
| not a fact-check (news report on Instagram censorship after the CJP pr | 1 |
| not a fact-check (news report on doxxing of women protesters) | 1 |
| not a fact-check (news feature on a university demolition dispute) | 1 |
| duplicate of https://www.altnews.in/the-law-bengal-cm-suvendu-adhikari | 1 |
| not a fact-check (news report on an assault incident in West Bengal) | 1 |
| not a fact-check (news report on a politician's remarks about proteste | 1 |
| not a fact-check (media criticism piece on TV coverage; no verdict on  | 1 |
| not a fact-check (news report and interview on a political party's soc | 1 |
| not a fact-check (news report on an FIR filed over controversial remar | 1 |
| not a fact-check (news report on arrests, bail hearings and political  | 1 |
| not a fact-check (news report on calls for violence by social media in | 1 |
| not a fact-check: opinion/news analysis of an assault incident and the | 1 |
| not a fact-check: media-coverage analysis/commentary on a news agency' | 1 |
| not a fact-check: straight news report on a Supreme Court judge's publ | 1 |
| not a fact-check: news round-up of celebrities supporting the protests | 1 |
| not a fact-check: straight news report on a police driver's suspension | 1 |
| not a fact-check: investigative ground report questioning police denia | 1 |
| not a fact-check; straight news report of a clash at a solidarity prot | 1 |
| not a fact-check; reported feature on hunger strikers at Jantar Mantar | 1 |
| not a fact-check; analytical explainer that problematises both sides'  | 1 |
| claim centres on distressing videos of a minor sexual-violence victim; | 1 |
| not a fact-check; ground report on a lynching and post-election intimi | 1 |
| claim primarily involves graphic sexual violence (video of a man whose | 1 |
| not a fact-check; news report on communal abuse and threats targeting  | 1 |
| Article centres on graphic beheading footage; excluded so the educatio | 1 |
| not a fact-check: investigative analysis of the account network behind | 1 |

<details><summary>full exclusion list</summary>

| url | reason |
| --- | --- |
| https://newschecker.in/fact-check/france-protests-ai-video-palestinian-flag-eiffel-tower/ | duplicate of the existing claims.json entry eiffel-tower-palestinian-flag-ai (same video, same claim) |
| https://newschecker.in/fact-check/weekly-wrap-misinformation-about-anti-cec-stir-cji-surya-kant-more/ | roundup, not a single claim |
| https://newschecker.in/fact-check/weekly-wrap-misinformation-around-jamui-molestation-case-rahul-gandhi-more/ | roundup, not a single claim |
| https://www.altnews.in/alok-bhatt-abusive-posts-withheld-x-handle-and-the-pamphlet-connection-no-one-wants-to-acknowledge/ | not a fact-check: investigative feature on the background and associations of a party social media appointee, no viral claim tested and no verdict |
| https://www.altnews.in/alt-news-impact-meta-removes-ai-manipulated-videos-of-women-from-jantar-mantar-protest/ | not a fact-check: follow-up impact story on a platform removing accounts, which aggregates earlier checks rather than testing a claim itself |
| https://www.altnews.in/another-attack-on-a-christian-family-in-bengal-woman-alleges-mob-assault-desecration-of-bible/ | not a fact-check (straight news report of an alleged attack and FIR) |
| https://www.altnews.in/apple-google-remove-bitchat-in-india-on-govt-order-those-determined-to-bypass-it-will-the-ordinary-user-gets-locked-out/ | not a fact-check |
| https://www.altnews.in/are-you-a-muslim-theatre-activist-beaten-in-bengal-after-he-replied-what-if-i-am-isnt-this-country-also-for-muslims/ | not a fact-check (news report on an assault incident in West Bengal) |
| https://www.altnews.in/arun-yadav-became-bjp-social-media-coordinator-deleted-60-thousand-old-tweets-abusive-and-racist-comments/ | not a fact-check (investigative report on deleted X posts, no verdict on a circulating claim) |
| https://www.altnews.in/as-bjp-wins-bengal-bypolls-facebook-restricts-pages-posts-alleging-rigging/ | not a fact-check |
| https://www.altnews.in/at-least-10-persons-suffered-pellet-injuries-on-sansad-chalo-march-20th-july-rti/ | not a fact-check (RTI-based news report, no verdict sentence on a circulating claim) |
| https://www.altnews.in/aur-nahi-marenge-they-said-and-then-kicked-slapped-brutalised-us-inside-a-pitch-dark-van-fitted-with-cages/ | not a fact-check; detainee testimonies of graphic violence |
| https://www.altnews.in/bangladesh-video-falsely-viral-as-kerala-man-attacked-by-daughters-over-sexual-abuse/ | claim primarily involves graphic sexual violence (video of a man whose genitals were severed); excluded to avoid amplifying it |
| https://www.altnews.in/beat-them-black-and-blue-how-hindutva-leader-pinky-chaudhary-others-called-for-violence-against-student-protesters/ | not a fact-check (news report on calls for violence by social media influencers) |
| https://www.altnews.in/bela-estate-farmland-and-homes-gone-728-delhi-pavement-dwellers-now-fight-to-retain-voting-rights/ | not a fact-check: news feature on voter-roll deletions affecting a slum cluster |
| https://www.altnews.in/bengal-bypolls-facebook-restricts-local-news-pages-covering-opposition-campaign-in-rejinagar/ | not a fact-check |
| https://www.altnews.in/bengal-bypolls-suvendu-adhikari-tells-minorities-to-pass-october-6-test-to-stay-with-government/ | not a fact-check: news report and commentary on a chief minister's bypoll appeal to minorities |
| https://www.altnews.in/bengal-christian-body-moves-nhrc-minority-commission-over-alleged-attacks-intimidation/ | not a fact-check |
| https://www.altnews.in/bengal-governors-office-essay-contest-asks-students-to-write-on-fatal-assault-on-civilisational-bharat/ | not a fact-check |
| https://www.altnews.in/bharpet-kha-lena-hi-jeevan-nahi-hai-mohammad-irfan-asks-india-to-listen/ | not a fact-check (human-interest profile of a private individual) |
| https://www.altnews.in/bjp-leader-ramesh-bidhuri-says-protesters-from-jantar-mantar-are-punctre-lagane-vale-tala-banane-vale-than-students/ | not a fact-check (news report on a politician's remarks about protesters) |
| https://www.altnews.in/bjp-men-led-the-group-that-raided-anandabazar-patrika-office-in-kolkata/ | not a fact-check: investigative news report identifying who led the newspaper office raid, not verification of a circulating claim |
| https://www.altnews.in/bjps-poll-spending-actor-involved-in-kolkata-beef-row-admits-to-taking-money-but-claims-it-was-not-for-the-pub-incident/ | not a fact-check: news report on a party's election-expenditure disclosure and the recipients' responses |
| https://www.altnews.in/bjps-violent-meme-war-aggressive-attacks-brand-opposition-dimaagi-naxals/ | not a fact-check: analysis piece on a party's social media campaign |
| https://www.altnews.in/bring-your-sisters-daughters-our-boys-are-also-ready-bjp-mlas-remark-on-muslims-attending-garba-sparks-row/ | not a fact-check: news report on a politician's communal remark and the ensuing backlash |
| https://www.altnews.in/christian-families-in-bengal-attacked-allege-rape-and-death-threats-by-bajrang-dal-members/ | not a fact-check (straight news report of alleged assault and FIR) |
| https://www.altnews.in/churches-vandalised-prayers-disrupted-pastors-beaten-up-christian-groups-in-bengal-face-hindutva-outfits-ire/ | not a fact-check: news report documenting attacks on Christian congregations in Bengal |
| https://www.altnews.in/cjp-activists-father-dies-after-alleged-assault-by-bjp-men-in-bengals-bankura-8-arrested/ | not a fact-check (straight news report of a fatal assault, with graphic violence and named private individuals) |
| https://www.altnews.in/cjp-stir-anti-national-anti-hindu-says-hindutva-outfit-chief-who-thrashed-two-students-at-jantar-mantar/ | not a fact-check: opinion/news analysis of an assault incident and the attacker's record, with no viral claim verified |
| https://www.altnews.in/cjp-workers-picked-up-by-cops-in-bengal-abdul-hafiz-detained-for-over-13-hours/ | not a fact-check |
| https://www.altnews.in/content-creators-decry-instagram-censorship-call-restrictions-a-digital-emergency/ | not a fact-check (reportage on platform censorship) |
| https://www.altnews.in/demolishing-a-varsity-dismantling-futures-the-story-of-mohammad-ali-jauhar-universitys-fight-for-survival/ | not a fact-check (news feature on a university demolition dispute) |
| https://www.altnews.in/demolition-of-book-stalls-continue-in-bengal-locals-resist-bulldozer-in-night-long-standoff-in-jadavpur/ | not a fact-check (straight news report) |
| https://www.altnews.in/despite-supreme-court-directive-delhi-police-detains-journalists-on-duty-on-second-consecutive-day/ | not a fact-check (straight news report) |
| https://www.altnews.in/detained-for-covering-a-protest-inside-delhi-polices-october-10-crackdown-on-journalists/ | not a fact-check |
| https://www.altnews.in/digitally-altered-video-of-sara-tendulkar-goes-viral/ | primarily sexualised digitally altered imagery of a named real person, excluded under content policy |
| https://www.altnews.in/discrepancy-in-nandigram-bjp-candidate-hashirani-raths-poll-affidavit-age-60-class-x-in-1965/ | not a fact-check: news report on a high court petition over a candidate's affidavit, with no conclusion reached |
| https://www.altnews.in/doctored-video-of-woman-bathing-in-ganga-in-bikini-goes-viral/ | sensitive content: the fact-checked item is a sexualised AI-doctored clip targeting an identifiable private woman who is a victim of image-based abuse, so it is not amplified on the dashboard |
| https://www.altnews.in/eating-chicken-on-ganga-cant-be-an-offence-no-law-bars-that-says-justice-ujjal-bhuyan/ | not a fact-check: straight news report on a Supreme Court judge's public lecture |
| https://www.altnews.in/eyes-wide-shut-on-july-20-ani-did-not-share-a-single-x-post-on-students-injured-in-delhi/ | not a fact-check: media-coverage analysis/commentary on a news agency's output, not a verdict on a circulating claim |
| https://www.altnews.in/forty-six-days-on-taps-in-kolkatas-jyotinagar-colony-still-run-dry/ | not a fact-check: news report on a water supply disruption and residents' allegations |
| https://www.altnews.in/go-back-to-your-country-manipuri-musicians-killing-reignites-concerns-over-racism-against-northeasterners-govt-inaction/ | not a fact-check: news report on a killing and discrimination against Northeasterners, centred on an identified victim |
| https://www.altnews.in/godi-media-haye-haye-to-heckling-on-the-ground-why-tv-reporters-became-a-target-during-cjp-protests/ | not a fact-check: media analysis/explainer on hostility toward TV reporters at protests, no viral claim verified and no verdict |
| https://www.altnews.in/government-orders-trigger-sweeping-instagram-censorship-days-after-cjp-protest/ | not a fact-check (news report on Instagram censorship after the CJP protests) |
| https://www.altnews.in/hans-raj-college-student-alleges-knife-attack-by-teenage-boy-from-hindutva-group-at-delhi-protest/ | not a fact-check; first-person account of graphic violence by a victim |
| https://www.altnews.in/hardoi-victims-hospital-bed-statement-falsely-linked-to-rajasthan-gangrape-case/ | claim centres on distressing videos of a minor sexual-violence victim; excluded to avoid amplifying such content |
| https://www.altnews.in/hindu-raksha-dal-chief-son-threaten-cjp-protesters-in-police-presence-outfit-member-assaults-protesters-in-delhi-streets/ | not a fact-check |
| https://www.altnews.in/how-dare-she-hindutva-flagbearers-threaten-muslim-judge-who-sent-14-cow-vigilantes-to-jail-for-murder/ | not a fact-check; news report on communal abuse and threats targeting a judge |
| https://www.altnews.in/hunt-for-a-global-toolkit-republic-blamed-everyone-from-us-deep-state-to-greta-thunberg-for-cjp-stir/ | not a fact-check (media criticism piece on TV coverage; no verdict on a specific claim) |
| https://www.altnews.in/in-24-delhi-constituencies-sir-draft-roll-has-fewer-names-than-2025-voter-turnout/ | not a fact-check: Alt News data-analysis report on Delhi SIR draft rolls that poses open questions to the Election Commission and reaches no verdict on a viral claim |
| https://www.altnews.in/in-dismissing-pellet-injuries-as-limited-damage-chauhaan-loses-sight-of-kashmirs-grim-brutal-reality/ | not a fact-check |
| https://www.altnews.in/instagram-censorship-puzzle-alt-news-post-survives-only-after-burhan-wani-is-removed/ | not a fact-check (first-person account of the outlet's own post being restricted) |
| https://www.altnews.in/instagram-takes-down-content-critical-of-vizag-data-centre-projects-cites-it-act-notices/ | not a fact-check |
| https://www.altnews.in/international-media-rights-bodies-flag-police-excesses-at-delhi-cjp-protest/ | not a fact-check (news report aggregating international reactions) |
| https://www.altnews.in/ips-officer-bushara-bano-transferred-after-right-wing-outrage-over-use-of-arabic-words-in-video-address-to-students/ | not a fact-check: news report on the transfer of an IPS officer after an online campaign |
| https://www.altnews.in/jadavpur-university-vandalism-abvp-leaders-bjp-functionaries-identified-in-cctv-footage/ | not a fact-check: investigative report identifying individuals in campus CCTV footage, no viral claim tested |
| https://www.altnews.in/jalil-akhtar-valid-indian-documents-cleared-sir-in-2002-2026-yet-arrested-as-a-bangladeshi/ | not a fact-check: news feature on an arrest and a pending citizenship case before a court |
| https://www.altnews.in/jamatis-islamists-friday-people-bengal-cms-communal-script-behind-the-crackdown-on-cjp-protesters/ | not a fact-check (news report on arrests, bail hearings and political rhetoric) |
| https://www.altnews.in/jamia-cracks-down-on-students-as-hunger-strike-police-action-and-campus-shutdown-deepen-crisis/ | not a fact-check (straight news report) |
| https://www.altnews.in/koi-media-nahi-hai-journalists-dragged-detained-demeaned-in-delhi-in-dark-day-for-worlds-largest-democracy/ | not a fact-check |
| https://www.altnews.in/lets-be-very-clear-cji-surya-kant-says-sc-did-not-approve-modified-form-6/ | not a fact-check |
| https://www.altnews.in/meet-priti-gandhi-the-huge-godse-fan-now-steering-bjps-social-media-cell/ | not a fact-check: profile/investigative report on a political appointee's past posts |
| https://www.altnews.in/meta-bans-posts-by-indian-youth-congress-aam-aadmi-party-and-other-leaders/ | not a fact-check: news report on platform restrictions of political parties' posts |
| https://www.altnews.in/mp-bhalaghat-deaths-of-adivasi-children-instagram-accounts-of-journalists-suspended/ | not a fact-check: news report on suspensions of independent journalists' Instagram accounts |
| https://www.altnews.in/mumbai-cop-threatens-youth-protestors-of-framing-them-in-fake-drug-cases-shunted-after-video-goes-viral/ | not a fact-check: straight news report on a police driver's suspension after a viral video |
| https://www.altnews.in/namo-seva-students-made-to-act-in-play-glorifying-modi-chant-modi-hai-toh-mumkin-hai-jai-sri-ram/ | not a fact-check |
| https://www.altnews.in/neha-manish-ameen-too-sonam-wangchuk-wasnt-the-only-hunger-strike-at-jantar-mantar/ | not a fact-check; reported feature on hunger strikers at Jantar Mantar |
| https://www.altnews.in/new-bjp-social-media-team-members-delete-or-hide-x-posts-deactivate-handles/ | not a fact-check (straight news report on party appointees deleting posts) |
| https://www.altnews.in/no-one-fired-pellet-guns-in-delhi/ | not a fact-check: investigative ground report questioning police denials; no verdict on a specific viral claim visible in the cached text |
| https://www.altnews.in/no-presidential-assent-to-goonda-act-its-still-a-bill-notes-calcutta-high-court/ | duplicate of https://www.altnews.in/the-law-bengal-cm-suvendu-adhikari-invoked-against-july-24-protesters-is-not-yet-law/ (same claim; kept the more substantive investigation) |
| https://www.altnews.in/nothing-communal-on-camera-victims-son-interrupts-bengal-bjp-mlas-jihadi-claim-over-titagarh-murder/ | not a fact-check: ground report on a murder case and an MLA's communal framing, with no verdict statement on a viral claim in the cached text |
| https://www.altnews.in/now-meta-restricts-reportage-on-delhi-police-crackdown-on-protesters-bans-posts-accounts-citing-it-rules/ | not a fact-check (straight news report) |
| https://www.altnews.in/only-hindus-will-live-in-bengal-and-enjoy-their-rights-avijit-das-and-the-campaign-for-hindu-banga/ | not a fact-check (investigative report on a group's communally inflammatory speeches) |
| https://www.altnews.in/only-muslims-in-bjps-cjp-protest-reel-govt-fears-unity-wants-to-reduce-movement-to-communal-narrative-says-neha-bora/ | not a fact-check (news report and interview on a political party's social media reel) |
| https://www.altnews.in/only-sanatanis-can-touch-durga-idols-announces-suvendu-adhikari-claims-its-nothing-communal/ | not a fact-check (straight news report of a politician's statement) |
| https://www.altnews.in/operation-sindoo-did-rajnath-singh-claim-no-soldiers-were-killed/ | not a fact-check; analytical explainer that problematises both sides' claims without a single verdict on a viral claim |
| https://www.altnews.in/pushed-into-no-mans-land-waded-through-mud-how-sahida-fakir-was-deported-to-bangladesh-at-midnight/ | not a fact-check: reported investigation into an alleged midnight deportation, built on the family's account, with no claim being verified |
| https://www.altnews.in/reality-check-for-mohan-bhagwat-muslims-threatened-by-bjp-mla-voters-targeted-for-deletion-fir-over-namaz-mosque-razed-in-up/ | not a fact-check: news roundup of recent incidents across several states |
| https://www.altnews.in/saffron-clad-men-gherao-anandabazar-patrika-office-in-kolkata-paint-walls-saffron/ | not a fact-check: straight news report of the incident at the newspaper office |
| https://www.altnews.in/sale-of-books-becomes-latest-political-flashpoint-in-bengal-as-left-stalls-face-attacks/ | not a fact-check (straight news report) |
| https://www.altnews.in/sonam-wangchuk-solidarity-protest-turns-violent-in-santiniketan-students-on-hunger-strike-allege-assault-by-abvp/ | not a fact-check; straight news report of a clash at a solidarity protest |
| https://www.altnews.in/taare-zameen-par-celebrities-break-silence-back-cjp-led-youth-uprising/ | not a fact-check: news round-up of celebrities supporting the protests |
| https://www.altnews.in/they-dragged-us-hit-us-with-batons-i-could-not-breathe-journalist-shaheen-khan-recounts-assault-at-saket-ps/ | not a fact-check: news report on alleged police assault on two journalists, contested by police |
| https://www.altnews.in/they-fear-cartoons-will-demolish-their-narratives-satish-acharya-on-govt-ordered-content-restrictions/ | not a fact-check |
| https://www.altnews.in/tracked-doxxed-put-on-tv-trial-how-women-cjp-protesters-were-hunted-down-by-the-right-wing-star-anchors/ | not a fact-check (news report on doxxing of women protesters) |
| https://www.altnews.in/two-varanasi-boat-cases-two-legal-paths-same-day-bail-for-five-two-months-in-jail-for-14-muslims/ | not a fact-check |
| https://www.altnews.in/vhp-bajrang-dal-attack-reading-session-in-ahmedabad-tear-malala-anne-frank-books/ | not a fact-check: straight news report of a disruption at a reading session and the surrounding controversy |
| https://www.altnews.in/weeks-of-threats-extortion-and-violence-preceded-lynching-of-71-year-old-sheikh-shah-alam-in-bengals-hooghly/ | not a fact-check; ground report on a lynching and post-election intimidation |
| https://www.altnews.in/would-have-shot-protesters-secular-women-enjoy-rape-right-wing-ideologue-t-g-mohandas-booked-over-controversial-remarks/ | not a fact-check (news report on an FIR filed over controversial remarks) |
| https://www.altnews.in/yati-narsinghanands-aide-anil-yadav-calls-for-annihilation-of-muslims-at-mahapanchayat/ | not a fact-check |
| https://www.altnews.in/youtuber-influencer-goon-activist-how-mainstream-media-sanitised-swatantra-bhardwaj/ | not a fact-check: media criticism piece on how outlets labelled an accused person |
| https://www.altnews.in/zee-news-fined-%e2%82%b92-lakh-for-inflammatory-amu-protest-coverage-asked-to-pull-down-content-within-seven-days/ | not a fact-check: news report on a broadcast regulator's penalty order against a channel |
| https://www.indiatoday.in/fact-check/story/eiffel-tower-palestine-flag-video-ai-generated-fact-check-3020908-2026-10-19 | duplicate of the existing claims.json entry eiffel-tower-palestinian-flag-ai (same video, same claim) |
| https://www.indiatoday.in/fact-check/story/saudi-arabia-2015-beheading-video-falsely-linked-bangladeshi-executions-3020954-2026-10-19 | Article centres on graphic beheading footage; excluded so the educational dashboard does not amplify violent content. |
| https://www.thequint.com/news/webqoof/neha-bora-targeted-by-misinformation-by-networks-france-24 | not a fact-check: investigative analysis of the account network behind a narrative, with no single claim or verdict, and it centres on targeted abuse of a named individual |
| https://www.thequint.com/news/webqoof/webqoof-recap-19-to-23-october-anti-cec-protest-ai-visuals-europe-protests | roundup, not a single claim |

</details>

## Candidates that were never usable

8 harvested candidates did not reach a reviewer.

| state | count |
| --- | --- |
| fetched OK but not reviewed | 8 |

These were dropped to keep the review effort inside the target record count, not because
they failed a quality check, except where the state above says otherwise.

## Sources that could not be harvested

| organisation | result |
| --- | --- |
| AFP Fact Check | HTTP 403 to automated fetchers; no candidates harvested |
| Reuters Fact Check | HTTP 401 to automated fetchers; no candidates harvested |
| AP News fact checks | HTTP 403 to automated fetchers; no candidates harvested |
| Logically Facts | connection failed; no candidates harvested |
| PIB Fact Check | JS-rendered listing with no article links or feed; pagination returns 404 |

No record in `claims.json` cites these organisations unless it was already present before
this expansion, in which case it is flagged `legacy` above.

