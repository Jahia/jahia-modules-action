/// @ts-check
/// 
import fs from 'node:fs';
import { defineConfig } from 'chachalog';
import github from 'chachalog/github';

export default defineConfig(() => ({
  allowedBumps: ['patch', 'minor', 'major'],
  platform: github(),
  managers: {
    packages: {
      name: 'test-chachalog-changelog',
      path: process.cwd(),
      version: fs.readFileSync('.chachalog/.version', 'utf-8').trim(),
    },
    setVersion(pkg, version) {
      fs.writeFileSync('.chachalog/.version', version);
      return true;
    },
  },
}));
