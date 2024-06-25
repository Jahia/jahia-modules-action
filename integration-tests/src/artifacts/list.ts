import {DefaultArtifactClient, Artifact} from '@actions/artifact';

export const listArtifacts = async (): Promise<Artifact[]> => {
    const artifactClient = new DefaultArtifactClient();
    const artifacts = await artifactClient.listArtifacts();
    return artifacts.artifacts;
}