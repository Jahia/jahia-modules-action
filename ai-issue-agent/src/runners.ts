// The runner flavours a dispatched session may run on, and the capacity of each. This list is the
// only source of `runs-on` for the execution workflow: the payload names a flavour, never a label,
// so a dispatch cannot start a runner outside it. The capacity mirrors the runner configs of
// Jahia/github-actions-runners (templates/runner-configs/<name>.yaml).
//
// A flavour enters the list with `agentSelectable: false` until the triage may pick it; a manual
// dispatch may still name it.

export interface RunnerFlavour {
  name: string
  // The labels of `runs-on`. Each flavour names its own label, because a job that asks for
  // `self-hosted` alone also fits an idle runner of another flavour.
  runsOn: string[]
  vcpu: number
  memoryGib: number
  instanceTypes: string[]
  agentSelectable: boolean
  // What the flavour suits, for the triage.
  use: string
}

export const DEFAULT_RUNNER = 'default'

export const RUNNER_FLAVOURS: readonly RunnerFlavour[] = [
  {
    name: 'default',
    runsOn: ['self-hosted', 'default'],
    vcpu: 8,
    memoryGib: 32,
    instanceTypes: ['t3a.2xlarge', 't3.2xlarge'],
    agentSelectable: true,
    use: 'a build, a test suite, or a Jahia instance in Docker',
  },
  {
    name: 'small',
    runsOn: ['self-hosted', 'small'],
    vcpu: 2,
    memoryGib: 8,
    instanceTypes: ['t3a.large', 't3.large'],
    agentSelectable: true,
    use: 'reading code and threads, writing a comment or a small edit, with no build',
  },
]

export const findRunner = (name: string): RunnerFlavour | undefined =>
  RUNNER_FLAVOURS.find((flavour) => flavour.name === name)

// The flavours the triage may pick, in the shape of the `runners` field of its context.
export const selectableRunners = (): {
  name: string
  vcpu: number
  memory_gib: number
  use: string
}[] =>
  RUNNER_FLAVOURS.filter((flavour) => flavour.agentSelectable).map((flavour) => ({
    name: flavour.name,
    vcpu: flavour.vcpu,
    memory_gib: flavour.memoryGib,
    use: flavour.use,
  }))
