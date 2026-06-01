#!/usr/bin/env python3
"""Generate postman/collections/tech-blog-api.postman_collection.json."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "collections" / "tech-blog-api.postman_collection.json"

PERF_ASSERT = [
    "const maxMs = parseInt(pm.environment.get('maxResponseMs') || '3000', 10);",
    "pm.test('Status is 200', function () { pm.response.to.have.status(200); });",
    "pm.test('Response time OK', function () {",
    "    pm.expect(pm.response.responseTime).to.be.below(maxMs);",
    "});",
]

STATUS_ONLY = [
    "pm.test('Status is 200', function () { pm.response.to.have.status(200); });",
]


def event(listen: str, lines: list[str]) -> dict:
    return {
        "listen": listen,
        "script": {"type": "text/javascript", "exec": lines},
    }


def request(
    name: str,
    method: str,
    url: str,
    *,
    tests: list[str] | None = None,
    prerequest: list[str] | None = None,
    body: str | None = None,
    noauth: bool = False,
) -> dict:
    events = []
    if prerequest:
        events.append(event("prerequest", prerequest))
    if tests:
        events.append(event("test", tests))
    req: dict = {
        "name": name,
        "request": {
            "method": method,
            "header": [],
            "url": url,
        },
        "response": [],
    }
    if events:
        req["event"] = events
    if noauth:
        req["request"]["auth"] = {"type": "noauth"}
    if body is not None:
        req["request"]["header"] = [{"key": "Content-Type", "value": "application/json"}]
        req["request"]["body"] = {"mode": "raw", "raw": body}
    return req


LOGIN_TESTS = [
    "pm.test('Login returns 200', function () { pm.response.to.have.status(200); });",
    "const body = pm.response.json();",
    "pm.expect(body.accessToken, 'accessToken present').to.be.a('string').and.not.empty;",
    "pm.environment.set('accessToken', body.accessToken);",
]

LOGIN_TESTS_PERF = LOGIN_TESTS + [
    "const maxMs = parseInt(pm.environment.get('maxResponseMs') || '3000', 10);",
    "pm.test('Login response time OK', function () {",
    "    pm.expect(pm.response.responseTime).to.be.below(maxMs);",
    "});",
]

LIST_USERS_TESTS = STATUS_ONLY + [
    "const body = pm.response.json();",
    "pm.expect(body.items).to.be.an('array');",
    "const username = pm.environment.get('username');",
    "const match = body.items.find(function (u) { return u.email === username; });",
    "if (match) { pm.environment.set('userId', match.userId); }",
]

LIST_USERS_TESTS_PERF = PERF_ASSERT + LIST_USERS_TESTS[1:]

GET_USER_TESTS = STATUS_ONLY + [
    "const body = pm.response.json();",
    "pm.environment.set('userEmail', body.email);",
    "pm.environment.set('userName', body.name || 'User');",
    "pm.environment.set('initialUserRole', body.role);",
    "pm.environment.set('userId', body.userId);",
]

GET_USER_TESTS_PERF = PERF_ASSERT + GET_USER_TESTS[1:]

SKIP_WITHOUT_USER = [
    "if (!pm.environment.get('userId')) { pm.execution.skipRequest(); }",
]

SKIP_WITHOUT_POST = [
    "if (!pm.environment.get('perfPostId')) { pm.execution.skipRequest(); }",
]

SKIP_DELETE_USER = [
    "const disposable = pm.environment.get('disposableUserId');",
    "const self = pm.environment.get('userId');",
    "if (!disposable || disposable === self) { pm.execution.skipRequest(); }",
    "pm.environment.set('userId', disposable);",
]

CREATE_POST_TESTS = STATUS_ONLY + [
    "const body = pm.response.json();",
    "pm.expect(body.postId).to.be.a('string').and.not.empty;",
    "pm.environment.set('perfPostId', body.postId);",
    "pm.environment.set('postId', body.postId);",
]

CREATE_POST_TESTS_PERF = PERF_ASSERT + CREATE_POST_TESTS[1:]

LOGIN_BODY = '{\n  "username": "{{username}}",\n  "password": "{{password}}"\n}'


def api_flow(*, perf: bool) -> list[dict]:
    assert_fn = PERF_ASSERT if perf else STATUS_ONLY
    login_tests = LOGIN_TESTS_PERF if perf else LOGIN_TESTS
    list_users = LIST_USERS_TESTS_PERF if perf else LIST_USERS_TESTS
    get_user = GET_USER_TESTS_PERF if perf else GET_USER_TESTS
    create_post = CREATE_POST_TESTS_PERF if perf else CREATE_POST_TESTS

    return [
        request(
            "01 Login",
            "POST",
            "{{baseUrl}}/auth/login",
            tests=login_tests,
            body=LOGIN_BODY,
            noauth=True,
        ),
        request("02 List users", "GET", "{{baseUrl}}/users", tests=list_users),
        request(
            "03 Get user",
            "GET",
            "{{baseUrl}}/users/{{userId}}",
            prerequest=SKIP_WITHOUT_USER,
            tests=get_user,
        ),
        request(
            "04 Update user",
            "PUT",
            "{{baseUrl}}/users/{{userId}}",
            prerequest=SKIP_WITHOUT_USER,
            tests=assert_fn,
            body='{\n  "email": "{{userEmail}}",\n  "name": "{{userName}}"\n}',
        ),
        request(
            "05 Update user role",
            "PUT",
            "{{baseUrl}}/users/{{userId}}/role",
            prerequest=SKIP_WITHOUT_USER,
            tests=assert_fn,
            body='{\n  "role": "{{initialUserRole}}"\n}',
        ),
        request(
            "06 List posts",
            "GET",
            "{{baseUrl}}/posts",
            tests=assert_fn
            + [
                "const body = pm.response.json();",
                "pm.expect(body.items).to.be.an('array');",
            ],
        ),
        request(
            "07 Create post",
            "POST",
            "{{baseUrl}}/posts",
            tests=create_post,
            body='{\n  "title": "Perf {{$timestamp}}",\n  "body": "Postman performance test"\n}',
        ),
        request(
            "08 Get post",
            "GET",
            "{{baseUrl}}/posts/{{perfPostId}}",
            prerequest=SKIP_WITHOUT_POST,
            tests=assert_fn,
        ),
        request(
            "09 Update post",
            "PUT",
            "{{baseUrl}}/posts/{{perfPostId}}",
            prerequest=SKIP_WITHOUT_POST,
            tests=assert_fn,
            body='{\n  "title": "Perf updated {{$timestamp}}",\n  "body": "Updated by Postman"\n}',
        ),
        request(
            "10 Delete post",
            "DELETE",
            "{{baseUrl}}/posts/{{perfPostId}}",
            prerequest=SKIP_WITHOUT_POST,
            tests=assert_fn,
        ),
        request(
            "11 Delete user (optional)",
            "DELETE",
            "{{baseUrl}}/users/{{userId}}",
            prerequest=SKIP_DELETE_USER,
            tests=assert_fn,
        ),
    ]


collection = {
    "info": {
        "_postman_id": "tech-blog-api-collection",
        "name": "Tech Blog API",
        "description": (
            "All REST endpoints from backend/api-spec.yaml.\n\n"
            "**Requires admin** Cognito user for full coverage (users list/role/delete).\n\n"
            "Folders:\n"
            "- `Smoke` — one pass, all APIs\n"
            "- `Performance - All APIs` — same flow with response-time assertions (CI pipeline)\n\n"
            "Optional env `disposableUserId` enables step 11 (DELETE user) on a throwaway account only."
        ),
        "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json",
    },
    "auth": {
        "type": "bearer",
        "bearer": [{"key": "token", "value": "{{accessToken}}", "type": "string"}],
    },
    "variable": [{"key": "baseUrl", "value": "{{baseUrl}}"}],
    "item": [
        {
            "name": "Auth",
            "item": [
                request(
                    "Login",
                    "POST",
                    "{{baseUrl}}/auth/login",
                    tests=LOGIN_TESTS,
                    body=LOGIN_BODY,
                    noauth=True,
                ),
            ],
        },
        {
            "name": "Smoke",
            "description": "Single-pass functional test for every API endpoint.",
            "item": api_flow(perf=False),
        },
        {
            "name": "Performance - All APIs",
            "description": (
                "Full API performance flow for CI. Creates then deletes a post each iteration. "
                "User delete runs only when disposableUserId is set."
            ),
            "item": api_flow(perf=True),
        },
    ],
}

OUT.write_text(json.dumps(collection, indent=2) + "\n", encoding="utf-8")
print(f"Wrote {OUT}")
