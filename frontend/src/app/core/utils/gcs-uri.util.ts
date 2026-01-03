/**
 * Utility functions for working with Google Cloud Storage URIs
 */

/**
 * Converts a GCS URI (gs://bucket/path) to an HTTP URL
 * @param gcsUri The GCS URI (e.g., "gs://rehearsed_avatars/ash.png")
 * @returns The HTTP URL (e.g., "https://storage.googleapis.com/rehearsed_avatars/ash.png")
 */
export function gcsUriToHttpUrl(gcsUri: string): string {
  if (!gcsUri || !gcsUri.startsWith('gs://')) {
    return gcsUri; // Return as-is if not a GCS URI
  }
  
  // Remove gs:// prefix
  const path = gcsUri.replace('gs://', '');
  
  // Split bucket and object path
  const [bucket, ...objectParts] = path.split('/');
  const objectPath = objectParts.join('/');
  
  // Construct HTTP URL
  return `https://storage.cloud.google.com/${bucket}/${objectPath}`;
}

