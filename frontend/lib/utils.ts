export function formatBytes(bytes: number, decimals = 1) {
  if (bytes === 0) return "0 B";
  const k = 1024;
  const dm = decimals < 0 ? 0 : decimals;
  const sizes = ["B", "KB", "MB", "GB", "TB"];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(dm)) + " " + sizes[i];
}

export const sleep = (ms: number) => new Promise((res) => setTimeout(res, ms));

export async function readFileHeadAsText(file: File, bytes = 1024) {
  return await new Promise<string>((resolve, reject) => {
    const slice = file.slice(0, bytes);
    const reader = new FileReader();
    reader.onload = (e) => resolve(e.target?.result as string);
    reader.onerror = reject;
    reader.readAsText(slice);
  });
}

export function isLikelyNdjson(sample: string, lines = 3) {
  const arr = sample.split("\n").slice(0, lines);
  return arr.every((line) => {
    if (!line.trim()) return true;
    try {
      JSON.parse(line);
      return true;
    } catch {
      return false;
    }
  });
}
