const apiBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL;

if (!apiBaseUrl) {
  throw new Error(
    "NEXT_PUBLIC_API_BASE_URL ist nicht gesetzt. Bitte die Variable in .env.local definieren."
  );
}

export const env = {
  apiBaseUrl,
  fakeTaskPoll: process.env.NEXT_PUBLIC_FAKE_TASK_POLL === "true",
};
