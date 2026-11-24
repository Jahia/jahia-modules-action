/** A repository that does not serve a file answers 404, or 401 and 403 when it would need an account. */
export const isAbsent = (response: Response): boolean => [401, 403, 404].includes(response.status)
