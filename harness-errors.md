1. ● oh-my-claudecode:pre-dev-agent(Generate spec document)
  ⎿  Initializing…
  ⎿  Error: Agent type 'oh-my-claudecode:pre-dev-agent' not found. Available agents: analyst, architect,
     claude-code-guide, code-reviewer, code-simplifier, critic, debugger, designer, document-specialist, executor,
     explore, Explore, general-purpose, git-master, Plan, planner, pre-dev-agent, progressive-planner, qa-tester,
     scaffold, scientist, security-reviewer, statusline-setup, study-agent, summarize-agent, test-engineer, tracer,
     verifier, writer
     为什么一上来直接调用omc的agent?
2. ● Web Search("AI question generation agent LLM knowledge extraction education tech stack 2025 2026")
  ⎿  Did 0 searches in 127ms

● Web Search("智能出题系统 大模型 知识抽取 RAG 技术架构 2025")
  ⎿  Did 0 searches in 115ms

● Web Search("GLM-4 API question generation prompt engineering lightweight architecture")
为什么做了0次搜索
3. predev阶段的头脑风暴是在skills里面完成的，而不是在subagent里面完成的，这是不对的，因为subagent的目的就是用来减少上下文，You do NOT ask questions — the calling skill handles all user interaction.，仔细的思考skills和subagent的分工
   1. 头脑风暴应该在subagent里面做，确认一下subagent可以和用户进行交互
4. CLAUDE.md 何时生成？如何更新？应该包含什么？
   1. 最起码要包含验证？还是我们的工作流编排里面要包含验证？
5. scaffold subagent 没有给我用git； 
6. scaffold subagent 我和他交互之后，没有办法继续执行subagent，反而要重新委托
7. scaffold subagent 的上下文缺失，subagent好像没有办法在主session里面进行交互
8. scaffold对工具链的调整可能影响到CLAUDE.md, 所以应该由scaffold来修改CLAUDE.md. 或者调用/init来生成CLAUDE.md
9. scaffold没有考虑开发所处的系统，是否使用git（强制使用）等要素，让AI也帮我想一些
10. 添加一个新的subagent，run&check, rc。 跑通所有的单元测试，集成测试，如果没有要生成一份错误报告，这样可以指导omc来修复。
11. runner每次碰到一个错误都要尝试写一个单元测试或者集成测试来复线错误。这些知识是需要不断的积累的
12. runner的核心目的就是始终保证系统可用
13. [ ] lsp还没弄