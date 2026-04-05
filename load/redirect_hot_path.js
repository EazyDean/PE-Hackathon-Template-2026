import http from "k6/http";
import { check, sleep } from "k6";

const baseUrl = (__ENV.BASE_URL || "http://localhost:5000").replace(/\/$/, "");
const targetVus = Number(__ENV.TARGET_VUS || 50);
const duration = __ENV.DURATION || "60s";
const warmCache = (__ENV.WARM_CACHE || "true").toLowerCase() === "true";

export const options = {
  vus: targetVus,
  duration,
  thresholds: {
    http_req_failed: ["rate<0.01"],
    http_req_duration: ["p(95)<750"],
  },
};

function jsonHeaders() {
  return {
    headers: {
      "Content-Type": "application/json",
    },
  };
}

export function setup() {
  const nonce = `${Date.now()}-${Math.floor(Math.random() * 100000)}`;

  const userResponse = http.post(
    `${baseUrl}/api/users`,
    JSON.stringify({
      username: `load-user-${nonce}`,
      email: `load-user-${nonce}@example.com`,
    }),
    jsonHeaders(),
  );

  check(userResponse, {
    "setup user created": (response) => response.status === 201,
  });

  const userId = userResponse.json("id");
  const urlResponse = http.post(
    `${baseUrl}/api/urls`,
    JSON.stringify({
      user_id: userId,
      original_url: `https://example.com/load/${nonce}`,
      title: "load-test-target",
    }),
    jsonHeaders(),
  );

  check(urlResponse, {
    "setup short url created": (response) => response.status === 201,
  });

  const shortCode = urlResponse.json("short_code");

  if (warmCache) {
    http.get(`${baseUrl}/${shortCode}`, { redirects: 0 });
  }

  return { shortCode };
}

export default function (data) {
  const response = http.get(`${baseUrl}/${data.shortCode}`, { redirects: 0 });

  check(response, {
    "redirect status is 302": (res) => res.status === 302,
    "cache header present": (res) => !!res.headers["X-Cache"],
  });

  sleep(1);
}
