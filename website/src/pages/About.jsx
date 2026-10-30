import StatusBadge from '../components/StatusBadge.jsx';
import claimData from '../data/claims.json';

export default function About() {
  const activeClaims = claimData.claims.filter((claim) => !claim.archived).length;

  return (
    <section className="about">
      <header className="page-head">
        <p className="page-kicker">ABOUT THE PROJECT</p>
        <h2>What Fake News Analyzer is, and what it is not</h2>
        <p className="page-sub">
          Seven short answers, written for a first-time reader, and then the two
          documented incidents that made this project worth building. The
          technical detail that used to sit on the homepage lives here now.
        </p>
      </header>

      <div className="about-grid">
        <article className="about-card">
          <span className="about-num">01</span>
          <h3>What is Fake News Analyzer?</h3>
          <p>
            Two separate tools under one roof. The first is a checker: you paste
            in a news story, or give it a link, and it tells you whether the
            story is <em>written</em> like the fake news it learned from. The
            second is a dashboard of claims that people have already investigated
            and matched against published evidence.
          </p>
          <p>
            The important part is the word <em>separate</em>. The checker never
            decides whether a specific claim is true. The dashboard is not
            powered by the checker.
          </p>
        </article>

        <article className="about-card">
          <span className="about-num">02</span>
          <h3>Why did we build it?</h3>
          <ul>
            <li>
              Fabricated and sensational stories travel faster than corrections,
              and most readers have no quick first-pass signal for whether a
              story deserves trust.
            </li>
            <li>
              Manual fact-checking is slow and scarce, so an instant screening
              step helps decide what is worth a closer look.
            </li>
            <li>
              A full pipeline was needed end to end: a trained model, a real API
              serving it, and an interface that explains its own limits.
            </li>
            <li>
              Being honest about uncertainty mattered more than pretending to be
              accurate: no confidence percentages, no verdicts dressed up as
              proof.
            </li>
          </ul>
        </article>

        <article className="about-card">
          <span className="about-num">03</span>
          <h3>How does it work?</h3>
          <ul>
            <li>
              You submit article text or a public article URL — one or the other,
              never both.
            </li>
            <li>
              For a link, the server checks the address is a public web page,
              fetches it with redirect and size limits, and extracts the readable
              article text first.
            </li>
            <li>
              The text is converted into features and handed to the saved
              classifier, which returns one of two labels.
            </li>
            <li>
              The browser shows the label, the disclaimer, and how many
              characters were actually read.
            </li>
            <li>
              Nothing is stored, and the model file itself is never sent to your
              browser — it stays on the server.
            </li>
          </ul>
        </article>

        <article className="about-card">
          <span className="about-num">04</span>
          <h3>The machine-learning model and technology used</h3>
          <p>
            The model is a <strong>pattern-based verdict</strong>: a TF-IDF plus
            linear support-vector classifier pipeline. In plain terms, it counts
            which words and word-pairs appear how often, weights them so rare
            phrasing matters more than common phrasing, and draws a line between
            “written like the fake stories in its training set” and “written like
            the real ones”. Headline style, vocabulary and structure are what it
            sees — never the facts.
          </p>
          <ul>
            <li>
              Output labels are fixed: <strong>0 = Potentially Fake</strong>,{' '}
              <strong>1 = Potentially Real</strong>.
            </li>
            <li>
              The trained pipeline is saved once as{' '}
              <code>ml/best_model.pkl</code> and loaded by the FastAPI backend.
            </li>
            <li>
              The classifier has no probability output, so the site shows no
              percentage. A number that looked like certainty would be invented.
            </li>
            <li>
              Stack: scikit-learn for the model, FastAPI and Uvicorn to serve it,
              React with Vite for the interface, hand-written CSS for the theme.
            </li>
          </ul>
        </article>

        <article className="about-card">
          <span className="about-num">05</span>
          <h3>How the fact-check dashboard works</h3>
          <p>
            Separately from the model, this is a manually reviewed list of
            circulating claims — {activeClaims} entries live right now — each one
            carrying a status, the organisation that checked it, the evidence
            behind the verdict and the dates it was added and last reviewed.
            Nothing here is monitored, scraped or updated automatically; a person
            edits the record file each week.
          </p>
          <p className="about-status-line">
            Four strict statuses, and the difference between them is the point:
          </p>
          <ul>
            <li>
              <StatusBadge status="unverified" /> reliable evidence does not yet
              establish the claim either way.
            </li>
            <li>
              <StatusBadge status="misleading" /> the framing omits or twists
              context, and there is evidence of that.
            </li>
            <li>
              <StatusBadge status="false" /> reliable evidence shows the claim is
              false.
            </li>
            <li>
              <StatusBadge status="verified" /> reliable evidence supports the
              claim as presented.
            </li>
          </ul>
          <p>
            <strong>Unverified is not false.</strong> A claim is never marked
            false because it is controversial, unfamiliar, popular, or flagged by
            the ML model — and never marked verified just because a fact-check
            wrote about it.
          </p>
        </article>

        <article className="about-card">
          <span className="about-num">06</span>
          <h3>Screening result vs. verified fact-check</h3>
          <div className="compare-grid">
            <div className="compare-col">
              <h4>A checker result</h4>
              <ul>
                <li>Produced in seconds, by software.</li>
                <li>About <em>how a story is written</em>.</li>
                <li>Answers: “does this deserve a closer look?”</li>
                <li>Can be wrong about an individual story.</li>
                <li>Not evidence of truth or of a lie.</li>
              </ul>
            </div>
            <div className="compare-col">
              <h4>A dashboard record</h4>
              <ul>
                <li>Produced by a person reviewing sources.</li>
                <li>About <em>what the claim actually asserts</em>.</li>
                <li>Answers: “what did the evidence show?”</li>
                <li>Cites a named fact-checker and a link.</li>
                <li>Carries a review date you can judge.</li>
              </ul>
            </div>
          </div>
          <p>
            If you run a story through the checker and it comes back{" "}
            <strong>Potentially Fake</strong>, that is a prompt to investigate —
            not a finding that the story is false. Only the second column involves
            evidence about the world.
          </p>
        </article>

        <article className="about-card">
          <span className="about-num">07</span>
          <h3>Limitations and responsible use</h3>
          <ul>
            <li>
              The model reads style, not facts. It has no knowledge of real
              events and cannot verify any claim.
            </li>
            <li>
              Its behaviour depends entirely on the training data; unfamiliar
              topics, satire, or writing that imitates a legitimate news style can
              be mislabelled.
            </li>
            <li>
              URL reading fails on JavaScript-heavy, paywalled or blocking sites.
              Pasting the article text is the fallback.
            </li>
            <li>
              The dashboard is a snapshot of a hand-kept file. Claims get
              re-reviewed on a weekly cadence, not continuously, so always check
              the review date.
            </li>
            <li>
              Never use a screening label to accuse a named person or outlet of
              fabricating something, and never treat this tool as the only source
              for an important decision.
            </li>
          </ul>
        </article>
      </div>

      <section className="case-studies" aria-labelledby="case-studies-heading">
        <p className="page-kicker">DOCUMENTED HISTORY</p>
        <h3 className="case-heading" id="case-studies-heading">
          Why this matters beyond the model
        </h3>
        <p className="case-intro">
          Misinformation in India is not an abstract accuracy problem. Two
          widely reported episodes shaped how this project thinks about the
          difference between a suspicious-looking story and a verified one. Both
          are summarised here exactly as the linked sources state them, and
          neither is presented as the single cause of what followed.
        </p>

        <div className="case-grid">
          <article className="case-card">
            <p className="case-where">Muzaffarnagar district, Uttar Pradesh</p>
            <h4 className="case-when">August – September 2013</h4>
            <p className="case-lede">
              Footage from another country was shared as though it had been
              filmed during the communal violence in front of the people sharing
              it.
            </p>

            <dl className="case-facts">
              <div>
                <dt>What circulated</dt>
                <dd>
                  A video presented as the killing of two boys from one
                  community in Muzaffarnagar. Reporting for The Hindu on 9
                  September 2013, the newspaper traced the clip to an incident
                  in Pakistan.
                </dd>
              </div>
              <div>
                <dt>What officials said</dt>
                <dd>
                  The same report quotes Uttar Pradesh Home Secretary Kamal
                  Saxena acknowledging that fake videos about communal clashes
                  were being circulated on social media to disturb communal
                  harmony.
                </dd>
              </div>
              <div>
                <dt>The human cost</dt>
                <dd>
                  Sixty-two people died in the violence, and tens of thousands
                  were driven from their homes into relief camps that stayed
                  open for months.
                </dd>
              </div>
              <div>
                <dt>What this does not show</dt>
                <dd>
                  The clip did not start the riots. BBC News reported in March
                  2016 that an inquiry attributed the failure to contain the
                  violence to police and intelligence shortcomings, beside the
                  political and social causes of the period. Misinformation was
                  one accelerant among several.
                </dd>
              </div>
            </dl>

            <p className="case-sources-label">Sources</p>
            <ul className="case-sources">
              <li>
                <a
                  href="https://www.thehindu.com/news/national/other-states/social-media-rife-with-inflammatory-material-in-muzaffarnagar/article5110034.ece"
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  The Hindu — <em>Social media rife with inflammatory material in
                  Muzaffarnagar</em> (9 September 2013)
                </a>
              </li>
              <li>
                <a
                  href="https://www.bbc.com/news/world-asia-india-35742334"
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  BBC News — inquiry report on the 2013 riots, 62 dead
                  (7 March 2016)
                </a>
              </li>
              <li>
                <a
                  href="https://en.wikipedia.org/wiki/2013_Muzaffarnagar_riots"
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  Wikipedia — 2013 Muzaffarnagar riots (compiled overview of the
                  death toll and displacement)
                </a>
              </li>
            </ul>
          </article>

          <article className="case-card">
            <p className="case-where">Assam, Maharashtra and other states</p>
            <h4 className="case-when">2018</h4>
            <p className="case-lede">
              Forwarded messages warning that strangers were abducting children
              moved faster than any police warning could, and people were killed
              on the strength of them.
            </p>

            <dl className="case-facts">
              <div>
                <dt>What circulated</dt>
                <dd>
                  WhatsApp forwards alleging child abductions, in local
                  languages, usually with an alarming picture and no named
                  source.
                </dd>
              </div>
              <div>
                <dt>A documented case</dt>
                <dd>
                  On 8 June 2018, Abhijeet Nath and Nilotpal Das were beaten to
                  death by a mob at Panjuri in Karbi Anglong, Assam. They had
                  travelled there to arrange fish samples for their work, The
                  Hindu reported. Sixteen people were arrested, BBC News said,
                  and an Assam court convicted 20 in April 2026.
                </dd>
              </div>
              <div>
                <dt>The wider toll</dt>
                <dd>
                  On 20 July 2018 BBC News reported that at least 18 people had
                  been killed across India since April that year in mob
                  lynchings connected to such rumours, adding that media tallies
                  put the number higher. Five more men had been killed in
                  Maharashtra weeks earlier; The Guardian reported a
                  2,000-strong mob killing one man in July.
                </dd>
              </div>
              <div>
                <dt>What changed</dt>
                <dd>
                  The same BBC report describes WhatsApp limiting how many chats
                  a message could be forwarded to at once and removing the quick
                  forward button, after the Indian government warned the company
                  of legal consequences.
                </dd>
              </div>
              <div>
                <dt>What this does not show</dt>
                <dd>
                  A forwarded message did not kill anyone on its own. Pre-existing
                  anxiety, mobs forming before police arrived and the absence of
                  any local fact-check were part of every case. Naming
                  misinformation as one factor is not the same as blaming a
                  platform for a murder.
                </dd>
              </div>
            </dl>

            <p className="case-sources-label">Sources</p>
            <ul className="case-sources">
              <li>
                <a
                  href="https://www.bbc.com/news/world-asia-india-44897714"
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  BBC News — <em>India lynchings: WhatsApp sets new rules after
                  mob killings</em> (20 July 2018)
                </a>
              </li>
              <li>
                <a
                  href="https://www.bbc.com/news/world-asia-india-44435127"
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  BBC News — <em>India WhatsApp &lsquo;child kidnap&rsquo;
                  rumours claim two more victims</em> (11 June 2018)
                </a>
              </li>
              <li>
                <a
                  href="https://www.bbc.com/news/world-asia-india-44678674"
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  BBC News — <em>India &lsquo;WhatsApp child abduction
                  rumours&rsquo;: Five more lynched</em> (2 July 2018)
                </a>
              </li>
              <li>
                <a
                  href="https://www.bbc.com/news/articles/cly07kk2pm2o"
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  BBC News — <em>Karbi Anglong lynching: Assam court convicts 20
                  for murder of Abhijeet and Nilotpal</em> (23 April 2026)
                </a>
              </li>
              <li>
                <a
                  href="https://www.thehindu.com/news/national/other-states/assam-lynching-sister-of-abhijeet-naths-fiance-recounts-phone-call-with-alleged-killer/article24164391.ece"
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  The Hindu — Assam lynching report (14 June 2018)
                </a>
              </li>
              <li>
                <a
                  href="https://www.theguardian.com/world/2018/jul/15/india-police-arrest-25-people-after-latest-whatsapp-mob-lynching-child-kidnapping-rumours"
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  The Guardian — 25 arrested after latest WhatsApp lynching
                  (15 July 2018)
                </a>
              </li>
            </ul>
          </article>
        </div>

        <p className="case-note">
          Both episodes turn on <strong>where a piece of content came from</strong>,
          not on how it is written. That is the line this project draws: the
          checker can tell you a story reads like the fake news it was trained
          on; only a person, checking provenance against evidence, can tell you
          that a real video belongs to a different country and a different year.
        </p>
      </section>

      <div className="notice-band">
        <strong>Use it as a first pass.</strong> A “Potentially Real” label is
        not a guarantee of accuracy, and a “Potentially Fake” label is not proof
        of a lie. Confirm anything important with reliable independent sources —
        the fact-checks linked from the dashboard are a good place to start.
      </div>
    </section>
  );
}
