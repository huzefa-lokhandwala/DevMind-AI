"""50-Question Benchmark Dataset for ProofOS RAG Evaluation."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class BenchmarkCase:
    """Represents a single evaluation test case."""

    id: int
    query: str
    category: str
    expected_files: list[str] = field(default_factory=list)
    expected_symbols: list[str] = field(default_factory=list)
    expected_routes: list[str] = field(default_factory=list)
    query_intent: str = "GENERAL_CODE_SEARCH"
    multi_hop: bool = False
    expect_insufficient_evidence: bool = False


PROOFOS_BENCHMARK_DATASET: list[BenchmarkCase] = [
    # Category 1: Symbol Location (Cases 1-5)
    BenchmarkCase(
        id=1,
        query="Where is the VerificationEngine class implemented?",
        category="Symbol location",
        expected_files=["lib/verification/engine.ts"],
        expected_symbols=["VerificationEngine"],
        query_intent="SYMBOL_LOCATION",
    ),
    BenchmarkCase(
        id=2,
        query="Where is Builder Score calculated?",
        category="Symbol location",
        expected_files=["lib/verification/scoring.ts"],
        expected_symbols=["ScoringService", "recalculateAndLogScore"],
        query_intent="SYMBOL_LOCATION",
    ),
    BenchmarkCase(
        id=3,
        query="Where is the GitHubIntegration class defined?",
        category="Symbol location",
        expected_files=["lib/integrations/github.ts"],
        expected_symbols=["GitHubIntegration"],
        query_intent="SYMBOL_LOCATION",
    ),
    BenchmarkCase(
        id=4,
        query="Where is VerificationPipeline implemented?",
        category="Symbol location",
        expected_files=["lib/verification/pipeline.ts"],
        expected_symbols=["VerificationPipeline", "processSubmission"],
        query_intent="SYMBOL_LOCATION",
    ),
    BenchmarkCase(
        id=5,
        query="Where is the generateProofHash function defined?",
        category="Symbol location",
        expected_files=["lib/verification/engine.ts"],
        expected_symbols=["generateProofHash"],
        query_intent="SYMBOL_LOCATION",
    ),

    # Category 2: API Route Discovery (Cases 6-10)
    BenchmarkCase(
        id=6,
        query="Which API route handles verification submissions for achievements?",
        category="API route discovery",
        expected_files=["app/api/verify/route.ts"],
        expected_routes=["/api/verify"],
        query_intent="API_ROUTE",
    ),
    BenchmarkCase(
        id=7,
        query="Which route performs GitHub sync?",
        category="API route discovery",
        expected_files=["app/api/sync/github/route.ts"],
        expected_routes=["/api/sync/github"],
        query_intent="API_ROUTE",
    ),
    BenchmarkCase(
        id=8,
        query="Where is the POST endpoint for verifying evidence?",
        category="API route discovery",
        expected_files=["app/api/verify/route.ts"],
        expected_routes=["/api/verify"],
        query_intent="API_ROUTE",
    ),
    BenchmarkCase(
        id=9,
        query="Which endpoint triggers background GitHub user synchronization?",
        category="API route discovery",
        expected_files=["app/api/sync/github/route.ts"],
        expected_routes=["/api/sync/github"],
        query_intent="API_ROUTE",
    ),
    BenchmarkCase(
        id=10,
        query="Find all API route files under app/api.",
        category="API route discovery",
        expected_files=["app/api/verify/route.ts", "app/api/sync/github/route.ts"],
        query_intent="API_ROUTE",
    ),

    # Category 3: Database Model Discovery (Cases 11-15)
    BenchmarkCase(
        id=11,
        query="Which Prisma models store achievements and evidence?",
        category="Database model discovery",
        expected_files=["prisma/schema.prisma"],
        expected_symbols=["Achievement", "Evidence"],
        query_intent="DATABASE_MODEL",
    ),
    BenchmarkCase(
        id=12,
        query="Which table stores builder score history in the database?",
        category="Database model discovery",
        expected_files=["prisma/schema.prisma"],
        expected_symbols=["BuilderScoreHistory"],
        query_intent="DATABASE_MODEL",
    ),
    BenchmarkCase(
        id=13,
        query="Where is the User model defined in Prisma schema?",
        category="Database model discovery",
        expected_files=["prisma/schema.prisma"],
        expected_symbols=["User"],
        query_intent="DATABASE_MODEL",
    ),
    BenchmarkCase(
        id=14,
        query="Which model links users to their GitHub repository metadata?",
        category="Database model discovery",
        expected_files=["prisma/schema.prisma"],
        expected_symbols=["Repository"],
        query_intent="DATABASE_MODEL",
    ),
    BenchmarkCase(
        id=15,
        query="Where are W3C Verifiable Credentials stored in the database schema?",
        category="Database model discovery",
        expected_files=["prisma/schema.prisma"],
        expected_symbols=["VerifiableCredential"],
        query_intent="DATABASE_MODEL",
    ),

    # Category 4: Function / Call Graph Tracing (Cases 16-20)
    BenchmarkCase(
        id=16,
        query="What functions does VerificationPipeline.processSubmission call?",
        category="Function/call graph tracing",
        expected_files=["lib/verification/pipeline.ts", "lib/verification/engine.ts", "lib/verification/scoring.ts"],
        expected_symbols=["verifyEvidenceSource", "generateProofHash", "recalculateAndLogScore"],
        query_intent="CALL_GRAPH",
        multi_hop=True,
    ),
    BenchmarkCase(
        id=17,
        query="Which method calculates the 5 component scores for a builder?",
        category="Function/call graph tracing",
        expected_files=["lib/verification/scoring.ts"],
        expected_symbols=["recalculateAndLogScore", "calculateBuilderScore"],
        query_intent="CALL_GRAPH",
    ),
    BenchmarkCase(
        id=18,
        query="What method constructs a W3C JSON-LD credential in engine.ts?",
        category="Function/call graph tracing",
        expected_files=["lib/verification/engine.ts"],
        expected_symbols=["generateVerifiableCredential"],
        query_intent="CALL_GRAPH",
    ),
    BenchmarkCase(
        id=19,
        query="Which function updates user totalCommits when GitHub sync finishes?",
        category="Function/call graph tracing",
        expected_files=["lib/integrations/github.ts"],
        expected_symbols=["syncUserData"],
        query_intent="CALL_GRAPH",
    ),
    BenchmarkCase(
        id=20,
        query="What calls occur inside POST handler in app/api/sync/github/route.ts?",
        category="Function/call graph tracing",
        expected_files=["app/api/sync/github/route.ts", "lib/integrations/github.ts", "lib/verification/scoring.ts"],
        expected_symbols=["syncUserData", "recalculateAndLogScore"],
        query_intent="CALL_GRAPH",
        multi_hop=True,
    ),

    # Category 5: Execution-Flow Tracing (Cases 21-25)
    BenchmarkCase(
        id=21,
        query="Trace the complete GitHub achievement flow from HTTP API request to public Passport rendering.",
        category="Execution-flow tracing",
        expected_files=["app/api/verify/route.ts", "lib/verification/pipeline.ts", "lib/verification/engine.ts", "lib/verification/scoring.ts", "app/u/[username]/page.tsx"],
        query_intent="EXECUTION_FLOW",
        multi_hop=True,
    ),
    BenchmarkCase(
        id=22,
        query="Trace the GitHub sync flow from API POST to profile update and score log.",
        category="Execution-flow tracing",
        expected_files=["app/api/sync/github/route.ts", "lib/integrations/github.ts", "lib/verification/scoring.ts"],
        query_intent="EXECUTION_FLOW",
        multi_hop=True,
    ),
    BenchmarkCase(
        id=23,
        query="Trace how evidence is verified and appended to an achievement.",
        category="Execution-flow tracing",
        expected_files=["lib/verification/pipeline.ts", "lib/verification/engine.ts"],
        query_intent="EXECUTION_FLOW",
        multi_hop=True,
    ),
    BenchmarkCase(
        id=24,
        query="Trace the database update chain when recalculateAndLogScore is invoked.",
        category="Execution-flow tracing",
        expected_files=["lib/verification/scoring.ts", "prisma/schema.prisma"],
        query_intent="EXECUTION_FLOW",
    ),
    BenchmarkCase(
        id=25,
        query="Trace how public visitors load a user's verified Builder Passport by username.",
        category="Execution-flow tracing",
        expected_files=["app/u/[username]/page.tsx", "prisma/schema.prisma"],
        query_intent="EXECUTION_FLOW",
    ),

    # Category 6: Repository Architecture Questions (Cases 26-30)
    BenchmarkCase(
        id=26,
        query="Where is the public Builder Passport rendered?",
        category="Repository architecture questions",
        expected_files=["app/passport/page.tsx", "app/b/[slug]/page.tsx", "app/u/[username]/page.tsx"],
        query_intent="ARCHITECTURE",
    ),
    BenchmarkCase(
        id=27,
        query="What is the distinction between /passport, /b/[slug], and /u/[username]?",
        category="Repository architecture questions",
        expected_files=["app/passport/page.tsx", "app/b/[slug]/page.tsx", "app/u/[username]/page.tsx"],
        query_intent="ARCHITECTURE",
    ),
    BenchmarkCase(
        id=28,
        query="How does ProofOS store builder score history across recalculations?",
        category="Repository architecture questions",
        expected_files=["lib/verification/scoring.ts", "prisma/schema.prisma"],
        query_intent="ARCHITECTURE",
    ),
    BenchmarkCase(
        id=29,
        query="What framework and ORM power the ProofOS web application?",
        category="Repository architecture questions",
        expected_files=["package.json", "prisma/schema.prisma"],
        query_intent="ARCHITECTURE",
    ),
    BenchmarkCase(
        id=30,
        query="Where is initial seed data generated for development testing?",
        category="Repository architecture questions",
        expected_files=["prisma/seed.ts"],
        query_intent="ARCHITECTURE",
    ),

    # Category 7: Production-vs-Test Discrimination (Cases 31-35)
    BenchmarkCase(
        id=31,
        query="Where is the production VerificationEngine class implemented vs unit tests?",
        category="Production-vs-test discrimination",
        expected_files=["lib/verification/engine.ts"],
        expected_symbols=["VerificationEngine"],
        query_intent="SYMBOL_LOCATION",
    ),
    BenchmarkCase(
        id=32,
        query="Find production scoring calculation logic, ignoring unit test mocks.",
        category="Production-vs-test discrimination",
        expected_files=["lib/verification/scoring.ts"],
        expected_symbols=["ScoringService"],
        query_intent="SYMBOL_LOCATION",
    ),
    BenchmarkCase(
        id=33,
        query="Where is the production GitHub pipeline implemented?",
        category="Production-vs-test discrimination",
        expected_files=["lib/integrations/githubPipeline.ts"],
        query_intent="SYMBOL_LOCATION",
    ),
    BenchmarkCase(
        id=34,
        query="Where is the production validation schema defined?",
        category="Production-vs-test discrimination",
        expected_files=["lib/validations/schemas.ts"],
        query_intent="SYMBOL_LOCATION",
    ),
    BenchmarkCase(
        id=35,
        query="Where are unit tests for verification located?",
        category="Production-vs-test discrimination",
        expected_files=["tests/verification.test.ts"],
        query_intent="SYMBOL_LOCATION",
    ),

    # Category 8: Ambiguous Symbol Names (Cases 36-40)
    BenchmarkCase(
        id=36,
        query="Where is processSubmission defined?",
        category="Ambiguous symbol names",
        expected_files=["lib/verification/pipeline.ts"],
        expected_symbols=["processSubmission"],
        query_intent="SYMBOL_LOCATION",
    ),
    BenchmarkCase(
        id=37,
        query="Where is recalculateAndLogScore implemented?",
        category="Ambiguous symbol names",
        expected_files=["lib/verification/scoring.ts"],
        expected_symbols=["recalculateAndLogScore"],
        query_intent="SYMBOL_LOCATION",
    ),
    BenchmarkCase(
        id=38,
        query="Where is syncUserData implemented?",
        category="Ambiguous symbol names",
        expected_files=["lib/integrations/github.ts"],
        expected_symbols=["syncUserData"],
        query_intent="SYMBOL_LOCATION",
    ),
    BenchmarkCase(
        id=39,
        query="Where is generateProofHash defined?",
        category="Ambiguous symbol names",
        expected_files=["lib/verification/engine.ts"],
        expected_symbols=["generateProofHash"],
        query_intent="SYMBOL_LOCATION",
    ),
    BenchmarkCase(
        id=40,
        query="Where is verifyEvidenceSource implemented?",
        category="Ambiguous symbol names",
        expected_files=["lib/verification/engine.ts"],
        expected_symbols=["verifyEvidenceSource"],
        query_intent="SYMBOL_LOCATION",
    ),

    # Category 9: Missing Information (Cases 41-45)
    BenchmarkCase(
        id=41,
        query="Where is the Rust FFI bindings file in ProofOS?",
        category="Missing information",
        expected_files=[],
        expect_insufficient_evidence=True,
        query_intent="GENERAL_CODE_SEARCH",
    ),
    BenchmarkCase(
        id=42,
        query="Where is the Solidity smart contract for proof verification?",
        category="Missing information",
        expected_files=[],
        expect_insufficient_evidence=True,
        query_intent="GENERAL_CODE_SEARCH",
    ),
    BenchmarkCase(
        id=43,
        query="Where is the AWS S3 image uploader module defined?",
        category="Missing information",
        expected_files=[],
        expect_insufficient_evidence=True,
        query_intent="GENERAL_CODE_SEARCH",
    ),
    BenchmarkCase(
        id=44,
        query="Where is the Redis cache manager configured in ProofOS?",
        category="Missing information",
        expected_files=[],
        expect_insufficient_evidence=True,
        query_intent="GENERAL_CODE_SEARCH",
    ),
    BenchmarkCase(
        id=45,
        query="Where is the PyTorch neural network model trained in ProofOS?",
        category="Missing information",
        expected_files=[],
        expect_insufficient_evidence=True,
        query_intent="GENERAL_CODE_SEARCH",
    ),

    # Category 10: Adversarial / Hallucination-Prone Queries (Cases 46-50)
    BenchmarkCase(
        id=46,
        query="Does generateProofHash use RSA-4096 asymmetric private key signing?",
        category="Adversarial/hallucination-prone queries",
        expected_files=["lib/verification/engine.ts"],
        expect_insufficient_evidence=True,
        query_intent="FUNCTION_BEHAVIOR",
    ),
    BenchmarkCase(
        id=47,
        query="How does /api/verify trigger the Rust engine?",
        category="Adversarial/hallucination-prone queries",
        expected_files=["app/api/verify/route.ts"],
        expect_insufficient_evidence=True,
        query_intent="API_ROUTE",
    ),
    BenchmarkCase(
        id=48,
        query="Is the SHA-256 proof hash in engine.ts completely deterministic when called twice with identical input?",
        category="Adversarial/hallucination-prone queries",
        expected_files=["lib/verification/engine.ts"],
        query_intent="FUNCTION_BEHAVIOR",
    ),
    BenchmarkCase(
        id=49,
        query="Where is the Bitcoin blockchain anchor transaction constructed?",
        category="Adversarial/hallucination-prone queries",
        expected_files=[],
        expect_insufficient_evidence=True,
        query_intent="GENERAL_CODE_SEARCH",
    ),
    BenchmarkCase(
        id=50,
        query="Does /api/verify call githubPipeline.ts directly?",
        category="Adversarial/hallucination-prone queries",
        expected_files=["app/api/verify/route.ts"],
        query_intent="CALL_GRAPH",
    ),
]
