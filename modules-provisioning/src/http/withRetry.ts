/** Run the operation again while it throws, at most `attempts` times, waiting longer each time. */
export const withRetry = async <T>(
  operation: () => Promise<T>,
  attempts: number,
  wait: (milliseconds: number) => Promise<void>,
  attempt = 1
): Promise<T> => {
  try {
    return await operation()
  } catch (error) {
    if (attempt >= attempts) throw error
    await wait(2000 * attempt)
    return withRetry(operation, attempts, wait, attempt + 1)
  }
}
