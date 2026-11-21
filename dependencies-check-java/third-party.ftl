<#-- One dependency per line, "groupId:artifactId<TAB>version<TAB>license|license", for src/report.py -->
<#list dependencyMap as e>
${e.getKey().groupId}:${e.getKey().artifactId}	${e.getKey().version}	${e.getValue()?join("|")?replace("\\s+", " ", "r")}
</#list>
