export const env = {
  apiBaseUrl: process.env.NEXT_PUBLIC_API_BASE_URL || "",
  fakeTaskPoll: process.env.NEXT_PUBLIC_FAKE_TASK_POLL === "true"
};
