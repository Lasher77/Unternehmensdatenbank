import clsx from 'clsx';

export type JobStatus = 'ready' | 'uploading' | 'processing' | 'done' | 'error';

export default function JobStatusBadge({ status }: { status: JobStatus }) {
  const map: Record<JobStatus, string> = {
    ready: 'bg-gray-200 text-gray-800',
    uploading: 'bg-blue-200 text-blue-800',
    processing: 'bg-yellow-200 text-yellow-800',
    done: 'bg-green-200 text-green-800',
    error: 'bg-red-200 text-red-800'
  };
  return <span className={clsx('px-2 py-1 rounded text-xs', map[status])}>{status}</span>;
}
