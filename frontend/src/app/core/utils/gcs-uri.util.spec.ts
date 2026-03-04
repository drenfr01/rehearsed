import { gcsUriToHttpUrl } from './gcs-uri.util';

describe('gcsUriToHttpUrl', () => {
  it('should convert a standard GCS URI to an HTTP URL', () => {
    const result = gcsUriToHttpUrl('gs://rehearsed_avatars/ash.png');
    expect(result).toBe('https://storage.cloud.google.com/rehearsed_avatars/ash.png');
  });

  it('should handle GCS URIs with nested paths', () => {
    const result = gcsUriToHttpUrl('gs://bucket/path/to/file.png');
    expect(result).toBe('https://storage.cloud.google.com/bucket/path/to/file.png');
  });

  it('should return empty string as-is', () => {
    expect(gcsUriToHttpUrl('')).toBe('');
  });

  it('should return non-GCS URIs unchanged', () => {
    expect(gcsUriToHttpUrl('https://example.com/image.png')).toBe('https://example.com/image.png');
    expect(gcsUriToHttpUrl('/local/path.png')).toBe('/local/path.png');
    expect(gcsUriToHttpUrl('avatar.png')).toBe('avatar.png');
  });

  it('should handle null/undefined input gracefully', () => {
    expect(gcsUriToHttpUrl(null as unknown as string)).toBe(null as unknown as string);
    expect(gcsUriToHttpUrl(undefined as unknown as string)).toBe(undefined as unknown as string);
  });

  it('should handle bucket-only URI', () => {
    const result = gcsUriToHttpUrl('gs://mybucket/');
    expect(result).toBe('https://storage.cloud.google.com/mybucket/');
  });
});
