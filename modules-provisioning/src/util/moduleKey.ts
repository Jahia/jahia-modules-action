export const moduleKey = ({groupId, artifactId}: {groupId: string; artifactId: string}): string =>
  `${groupId}:${artifactId}`
