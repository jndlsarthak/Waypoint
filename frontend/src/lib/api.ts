export type Category = "factual" | "individualized_advice" | "out_of_scope";

export type Source = {
  n: number;
  url: string;
  page_title: string;
  section_heading: string;
  date_last_modified: string | null;
};

export type TemporalConflict = {
  source_n_a: number;
  source_n_b: number;
  date_a: string;
  date_b: string;
  url_a: string;
  url_b: string;
};

export type AnswerResponse = {
  answer: string;
  category: Category;
  sources: Source[];
  temporal_conflicts: TemporalConflict[];
};

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000";

export async function askQuestion(
  question: string,
  topK = 5,
): Promise<AnswerResponse> {
  const res = await fetch(`${API_BASE_URL}/query`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question, top_k: topK }),
  });

  if (!res.ok) {
    throw new Error(
      `The assistant API returned an error (${res.status}). Is the backend running at ${API_BASE_URL}?`,
    );
  }

  return res.json();
}
