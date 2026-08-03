"use client";

import { FormEvent, useState } from "react";

type Result = {
  file: string;
  lines: string;
  embedding: string;
  rerank: string;
  language: string;
  code: string;
};

const results: Result[] = [
  {
    file: "packages/core/src/lib/Stagehand.ts",
    lines: "Lines 141-169",
    embedding: "0.78",
    rerank: "0.98",
    language: "TypeScript",
    code: `async screenshot(options?: ScreenshotOptions) {
  const page = await this.page();
  return page.screenshot({
    fullPage: options?.fullPage ?? false,
    path: options?.path,
    type: options?.type ?? "png",
  });
}`,
  },
  {
    file: "packages/core/src/lib/handlers/screenshot.ts",
    lines: "Lines 18-52",
    embedding: "0.74",
    rerank: "0.95",
    language: "TypeScript",
    code: `export async function captureScreenshot(
  page: Page,
  options: ScreenshotOptions,
) {
  const buffer = await page.screenshot(options);
  return { buffer, mimeType: "image/png" };
}`,
  },
  {
    file: "packages/core/src/index.ts",
    lines: "Lines 62-88",
    embedding: "0.81",
    rerank: "0.90",
    language: "TypeScript",
    code: `export { Stagehand } from "./lib/Stagehand";
export type {
  StagehandConfig,
  ScreenshotOptions,
} from "./types";`,
  },
];

const vectorResults = [
  ["packages/core/src/index.ts", "0.81"],
  ["packages/core/src/lib/Stagehand.ts", "0.78"],
  ["packages/core/src/lib/handlers/screenshot.ts", "0.74"],
];

function Mark({ type }: { type: "arrow" | "search" | "copy" | "github" | "check" }) {
  const paths = {
    arrow: <path d="M5 12h14M13 6l6 6-6 6" />,
    search: <><circle cx="11" cy="11" r="6.5" /><path d="m16 16 4 4" /></>,
    copy: <><rect x="8" y="8" width="11" height="11" rx="1" /><path d="M16 8V5a1 1 0 0 0-1-1H5a1 1 0 0 0-1 1v10a1 1 0 0 0 1 1h3" /></>,
    github: <><path d="M12 2a10 10 0 0 0-3.16 19.49c.5.1.68-.22.68-.48v-1.7c-2.78.6-3.37-1.18-3.37-1.18-.45-1.16-1.11-1.47-1.11-1.47-.91-.62.07-.61.07-.61 1 .07 1.54 1.04 1.54 1.04.9 1.53 2.35 1.09 2.92.83.1-.66.35-1.1.64-1.36-2.22-.25-4.56-1.12-4.56-4.95 0-1.1.39-2 1.03-2.7-.1-.25-.45-1.28.1-2.67 0 0 .84-.27 2.75 1.03A9.5 9.5 0 0 1 12 6.8c.85 0 1.7.11 2.5.34 1.91-1.3 2.75-1.03 2.75-1.03.55 1.39.2 2.42.1 2.67.64.7 1.03 1.6 1.03 2.7 0 3.84-2.35 4.69-4.58 4.94.36.31.68.91.68 1.83v2.72c0 .26.18.58.69.48A10 10 0 0 0 12 2Z" /></>,
    check: <path d="m5 12 4.2 4L19 6.5" />,
  };
  return <svg viewBox="0 0 24 24" aria-hidden="true" className="h-4 w-4 fill-none stroke-current stroke-[1.8]">{paths[type]}</svg>;
}

export default function Home() {
  const [repository, setRepository] = useState("https://github.com/browserbase/stagehand");
  const [indexState, setIndexState] = useState<"idle" | "indexing" | "ready">("ready");
  const [query, setQuery] = useState("Where are screenshots captured?");
  const [submittedQuery, setSubmittedQuery] = useState("Where are screenshots captured?");
  const [view, setView] = useState<"reranked" | "vector">("reranked");
  const [copied, setCopied] = useState<string | null>(null);

  function indexRepository() {
    setIndexState("indexing");
    window.setTimeout(() => setIndexState("ready"), 1800);
  }

  function search(event: FormEvent) {
    event.preventDefault();
    if (query.trim()) setSubmittedQuery(query.trim());
  }

  async function copySnippet(result: Result) {
    await navigator.clipboard.writeText(result.code);
    setCopied(result.file);
    window.setTimeout(() => setCopied(null), 1500);
  }

  return (
    <main className="min-h-screen overflow-hidden bg-[#f5f4ed] text-[#171816]">
      <div className="page-grid pointer-events-none fixed inset-0 opacity-70" />
      <header className="relative mx-auto flex max-w-[1440px] items-center justify-between px-5 py-5 sm:px-8 lg:px-12">
        <a href="#top" className="flex items-center gap-2.5" aria-label="RepoRanker home">
          <span className="grid h-8 w-8 place-items-center bg-[#1d211b] text-[#d5ff45]"><span className="text-lg font-semibold leading-none">R</span></span>
          <span className="text-[15px] font-semibold tracking-[-0.04em]">RepoRanker</span>
        </a>
        <div className="hidden items-center gap-6 text-xs font-medium text-[#53564e] sm:flex">
          <span>Retrieval pipeline</span>
          <span className="rounded-full border border-[#c7c8bd] px-3 py-1.5 font-mono text-[10px] text-[#30332d]">v0.1.0</span>
        </div>
      </header>

      <section id="top" className="relative mx-auto max-w-[1440px] px-5 pb-14 pt-12 sm:px-8 sm:pt-20 lg:px-12 lg:pb-20">
        <div className="absolute -right-24 top-6 h-80 w-80 rounded-full bg-[#d5ff45] opacity-65 blur-[100px]" />
        <div className="relative grid gap-12 lg:grid-cols-[1.15fr_.85fr] lg:items-end">
          <div>
            <p className="mb-5 flex items-center gap-2 font-mono text-[11px] uppercase tracking-[0.16em] text-[#61645b]"><span className="h-1.5 w-1.5 rounded-full bg-[#92bc00]" /> Cohere-powered retrieval</p>
            <h1 className="max-w-4xl text-balance text-[clamp(3.7rem,8vw,7.8rem)] font-medium leading-[0.84] tracking-[-0.085em]">Search code.<br /><span className="text-[#758c18]">Find intent.</span></h1>
            <p className="mt-8 max-w-xl text-pretty text-base leading-7 text-[#54574f] sm:text-lg">An end-to-end retrieval pipeline for source code. Embed, retrieve, and rerank the signals that matter.</p>
          </div>
          <div className="border-l border-[#c8c9bd] pl-5 lg:mb-1">
            <p className="font-mono text-[11px] uppercase tracking-[0.12em] text-[#62655c]">Pipeline</p>
            <p className="mt-3 text-sm leading-6 text-[#454940]">GitHub ingestion <span className="px-1 text-[#91a719]">/</span> Cohere Embed <span className="px-1 text-[#91a719]">/</span> Pinecone <span className="px-1 text-[#91a719]">/</span> Cohere Rerank</p>
          </div>
        </div>
      </section>

      <section className="relative border-y border-[#cbccc1] bg-[#eeeee7]" aria-labelledby="repository-heading">
        <div className="mx-auto grid max-w-[1440px] gap-8 px-5 py-8 sm:px-8 lg:grid-cols-[.72fr_1.28fr] lg:px-12 lg:py-10">
          <div>
            <p className="font-mono text-[11px] uppercase tracking-[0.15em] text-[#66695f]">01 / Ingest</p>
            <h2 id="repository-heading" className="mt-3 text-2xl font-medium tracking-[-0.05em]">Index a repository</h2>
            <p className="mt-2 max-w-xs text-sm leading-6 text-[#62645d]">Clone a public GitHub repository and turn its code into searchable context.</p>
          </div>
          <div className="self-center">
            <div className="flex flex-col gap-3 sm:flex-row">
              <label className="sr-only" htmlFor="repository">GitHub repository URL</label>
              <div className="flex min-w-0 flex-1 items-center gap-3 border border-[#bdbeb4] bg-[#f7f7f2] px-4 py-3.5 shadow-[3px_3px_0_#d3d4c8]">
                <Mark type="github" />
                <input id="repository" value={repository} onChange={(event) => setRepository(event.target.value)} className="min-w-0 flex-1 bg-transparent font-mono text-xs outline-none placeholder:text-[#909188]" />
              </div>
              <button onClick={indexRepository} disabled={indexState === "indexing"} className="group inline-flex items-center justify-center gap-2 bg-[#1d211b] px-5 py-3.5 text-sm font-medium text-[#f5f4ed] transition hover:bg-[#718617] disabled:cursor-wait">
                {indexState === "indexing" ? "Indexing 62%" : "Index repository"}<Mark type="arrow" />
              </button>
            </div>
            {indexState === "indexing" ? <div className="mt-4 h-1 overflow-hidden bg-[#d8d9ce]"><div className="h-full w-[62%] bg-[#9cb900] transition-all" /></div> : <div className="mt-5 flex flex-wrap items-center gap-x-6 gap-y-2 text-xs text-[#5f6259]"><span className="inline-flex items-center gap-1.5 font-medium text-[#4c6513]"><span className="grid h-4 w-4 place-items-center rounded-full bg-[#d5ff45]"><Mark type="check" /></span> Repository indexed</span><span><b className="font-mono font-medium text-[#1c211b]">428</b> files</span><span><b className="font-mono font-medium text-[#1c211b]">3,184</b> chunks</span><span><b className="font-mono font-medium text-[#1c211b]">15.7s</b> embedding time</span></div>}
          </div>
        </div>
      </section>

      <section className="relative mx-auto max-w-[1440px] px-5 py-14 sm:px-8 lg:px-12 lg:py-20" aria-labelledby="search-heading">
        <div className="mb-8 flex flex-col justify-between gap-4 sm:flex-row sm:items-end">
          <div>
            <p className="font-mono text-[11px] uppercase tracking-[0.15em] text-[#66695f]">02 / Retrieve</p>
            <h2 id="search-heading" className="mt-3 text-3xl font-medium tracking-[-0.06em] sm:text-4xl">Search by meaning</h2>
          </div>
          <p className="font-mono text-[11px] text-[#6a6d63]">20 candidates / 5 reranked results</p>
        </div>
        <form onSubmit={search} className="flex flex-col border border-[#1d211b] bg-[#fbfaf5] p-2 shadow-[5px_5px_0_#d5ff45] sm:flex-row">
          <label className="sr-only" htmlFor="query">Search query</label>
          <div className="flex flex-1 items-center gap-3 px-3 py-2"><Mark type="search" /><input id="query" value={query} onChange={(event) => setQuery(event.target.value)} className="w-full bg-transparent text-base outline-none placeholder:text-[#8a8c83] sm:text-lg" /></div>
          <button type="submit" className="bg-[#d5ff45] px-6 py-3 text-sm font-semibold transition hover:bg-[#c1ed25]">Search</button>
        </form>
        <div className="mt-5 flex flex-wrap gap-2"><span className="mr-1 self-center font-mono text-[10px] uppercase tracking-[0.12em] text-[#767970]">Try</span>{["clipboard handling", "browser sessions", "macro recording"].map((suggestion) => <button key={suggestion} onClick={() => { setQuery(`Where is ${suggestion} implemented?`); setSubmittedQuery(`Where is ${suggestion} implemented?`); }} className="border border-[#cbccc1] px-3 py-1.5 text-xs text-[#4f524b] transition hover:border-[#92a926] hover:bg-[#edf4cb]">{suggestion}</button>)}</div>
      </section>

      <section className="relative border-t border-[#cbccc1] bg-[#e8e9e1]" aria-label="Search results">
        <div className="mx-auto max-w-[1440px] px-5 py-10 sm:px-8 lg:px-12 lg:py-14">
          <div className="mb-7 flex flex-col justify-between gap-3 sm:flex-row sm:items-center"><div><p className="font-mono text-[11px] uppercase tracking-[0.15em] text-[#66695f]">03 / Rank</p><h2 className="mt-2 text-lg font-medium tracking-[-0.03em]">Results for <span className="text-[#718617]">“{submittedQuery}”</span></h2></div><p className="font-mono text-[11px] text-[#676a60]">247 ms total query latency</p></div>
          <div className="grid gap-8 xl:grid-cols-[1fr_2fr]">
            <aside className="border border-[#c5c6bc] bg-[#f5f4ed] p-5">
              <div className="flex border-b border-[#d4d5cb]"><button onClick={() => setView("reranked")} className={`-mb-px border-b-2 px-0 pb-3 pr-5 text-sm font-medium ${view === "reranked" ? "border-[#1d211b] text-[#1d211b]" : "border-transparent text-[#74766d]"}`}>After Rerank</button><button onClick={() => setView("vector")} className={`-mb-px border-b-2 px-0 pb-3 pl-4 text-sm font-medium ${view === "vector" ? "border-[#1d211b] text-[#1d211b]" : "border-transparent text-[#74766d]"}`}>Raw vector</button></div>
              <p className="mt-5 text-xs leading-5 text-[#686b61]">{view === "reranked" ? "Cohere Rerank promotes the code most likely to answer your question." : "Pinecone returns candidates by embedding similarity alone."}</p>
              <div className="mt-5 space-y-2">{(view === "reranked" ? results.map((result) => [result.file, result.rerank]) : vectorResults).map(([file, score], index) => <div key={file} className="flex items-center gap-3 border-l-2 border-[#b4ca35] bg-[#ebede2] px-3 py-3"><span className="font-mono text-[10px] text-[#75786e]">0{index + 1}</span><span className="min-w-0 flex-1 truncate text-xs font-medium">{file.split("/").pop()}</span><span className="font-mono text-xs text-[#668014]">{score}</span></div>)}</div>
              <div className="mt-6 border-t border-[#d4d5cb] pt-4"><div className="flex justify-between text-[11px] text-[#6e7168]"><span>Embed retrieval</span><span className="font-mono">91 ms</span></div><div className="mt-2 flex justify-between text-[11px] text-[#6e7168]"><span>Rerank inference</span><span className="font-mono">104 ms</span></div></div>
            </aside>
            <div className="space-y-4">{results.map((result, index) => <article key={result.file} className="group border border-[#c7c8be] bg-[#f8f7f2] transition hover:border-[#99b51f] hover:shadow-[4px_4px_0_#d5ff45]"><div className="flex flex-wrap items-center gap-x-4 gap-y-2 border-b border-[#d7d8ce] px-5 py-4"><span className="font-mono text-[10px] text-[#74776d]">0{index + 1}</span><span className="min-w-0 flex-1 truncate text-sm font-semibold tracking-[-0.02em]">{result.file}</span><span className="rounded-full border border-[#cfd0c6] px-2 py-1 font-mono text-[10px] text-[#5f6259]">{result.language}</span><button onClick={() => copySnippet(result)} className="inline-flex items-center gap-1.5 text-xs text-[#5c6057] hover:text-[#1c211b]">{copied === result.file ? <Mark type="check" /> : <Mark type="copy" />}{copied === result.file ? "Copied" : "Copy"}</button></div><div className="grid grid-cols-[1fr_auto] gap-4 px-5 py-3 text-xs sm:grid-cols-[1fr_auto_auto_auto]"><span className="font-mono text-[#74766d]">{result.lines}</span><span className="text-[#696c62]">Embed <b className="ml-1 font-mono font-medium text-[#1d211b]">{result.embedding}</b></span><span className="text-[#596b1c]">Rerank <b className="ml-1 font-mono font-medium text-[#455c08]">{result.rerank}</b></span></div><pre className="overflow-x-auto border-t border-[#e0e1d7] bg-[#20231e] px-5 py-4 font-mono text-[11px] leading-5 text-[#e3e6d8]"><code>{result.code}</code></pre></article>)}</div>
          </div>
        </div>
      </section>

      <footer className="relative mx-auto flex max-w-[1440px] flex-col gap-3 px-5 py-8 text-xs text-[#6d7067] sm:flex-row sm:items-center sm:justify-between sm:px-8 lg:px-12"><span>RepoRanker <span className="mx-2 text-[#a1a399]">/</span> A source-code retrieval system</span><span className="font-mono text-[10px] uppercase tracking-[0.12em]">Cohere Embed + Rerank</span></footer>
    </main>
  );
}
