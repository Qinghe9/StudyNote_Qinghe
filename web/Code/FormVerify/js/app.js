const state = {
  model: null,
  tempEmailDomains: new Set(),
  passwordResult: {
    label: "",
    score: 0,
    reasons: []
  },
  emailResult: {
    ok: false,
    risky: false,
    message: ""
  }
};

const COMMON_WEAK_WORDS = [
  "password",
  "admin",
  "qwerty",
  "abc",
  "test",
  "student",
  "user",
  "letmein",
  "welcome",
  "iloveyou"
];

const KEYBOARD_PATTERNS = [
  "qwerty",
  "asdf",
  "zxcv",
  "qaz",
  "wsx",
  "1234",
  "abcd"
];

const CLASS_TEXT = {
  weak: "弱密码",
  medium: "中等强度",
  strong: "强密码"
};

const fields = {
  form: document.querySelector("#registerForm"),
  username: document.querySelector("#username"),
  email: document.querySelector("#email"),
  password: document.querySelector("#password"),
  confirmPassword: document.querySelector("#confirmPassword"),
  usernameHint: document.querySelector("#usernameHint"),
  emailHint: document.querySelector("#emailHint"),
  passwordHint: document.querySelector("#passwordHint"),
  confirmHint: document.querySelector("#confirmHint"),
  strengthBar: document.querySelector("#strengthBar"),
  adviceList: document.querySelector("#adviceList"),
  submitMessage: document.querySelector("#submitMessage"),
  togglePassword: document.querySelector("#togglePassword"),
  passwordBadge: document.querySelector("#passwordBadge"),
  emailBadge: document.querySelector("#emailBadge"),
  modelStatus: document.querySelector("#modelStatus"),
  emailStatus: document.querySelector("#emailStatus"),
  modelDot: document.querySelector("#modelDot"),
  emailDot: document.querySelector("#emailDot")
};

function hasSequence(text) {
  const value = String(text || "").toLowerCase();

  for (let index = 0; index < value.length - 2; index += 1) {
    const a = value.charCodeAt(index);
    const b = value.charCodeAt(index + 1);
    const c = value.charCodeAt(index + 2);

    if (b === a + 1 && c === b + 1) {
      return true;
    }

    if (b === a - 1 && c === b - 1) {
      return true;
    }
  }

  return false;
}

function hasRepeated(text) {
  const value = String(text || "");

  for (let index = 0; index < value.length - 2; index += 1) {
    if (value[index] === value[index + 1] && value[index] === value[index + 2]) {
      return true;
    }
  }

  return false;
}

function extractFeatures(password) {
  const p = String(password || "");
  const lower = p.toLowerCase();
  const length = p.length;
  const lenBucket = length < 8 ? "short" : length <= 11 ? "medium" : "long";
  const hasLower = /[a-z]/.test(p);
  const hasUpper = /[A-Z]/.test(p);
  const hasDigit = /\d/.test(p);
  const hasSymbol = /[^A-Za-z0-9]/.test(p);
  const categories = [hasLower, hasUpper, hasDigit, hasSymbol].filter(Boolean).length;
  const mixBucket = categories <= 1 ? "single" : categories === 2 ? "double" : categories === 3 ? "triple" : "quad";
  const containsCommon = COMMON_WEAK_WORDS.some((word) => lower.includes(word));
  const keyboard = KEYBOARD_PATTERNS.some((pattern) => lower.includes(pattern));
  const yearLike = Array.from({ length: 41 }, (_, index) => String(1990 + index)).some((year) => p.includes(year));

  return [
    `len=${lenBucket}`,
    `mix=${mixBucket}`,
    `lower=${hasLower ? "yes" : "no"}`,
    `upper=${hasUpper ? "yes" : "no"}`,
    `digit=${hasDigit ? "yes" : "no"}`,
    `symbol=${hasSymbol ? "yes" : "no"}`,
    `common=${containsCommon ? "yes" : "no"}`,
    `repeat=${hasRepeated(p) ? "yes" : "no"}`,
    `sequence=${hasSequence(p) ? "yes" : "no"}`,
    `keyboard=${keyboard ? "yes" : "no"}`,
    `year=${yearLike ? "yes" : "no"}`
  ];
}

function getPasswordRules(password) {
  const value = String(password || "");
  const lower = value.toLowerCase();
  const hasLower = /[a-z]/.test(value);
  const hasUpper = /[A-Z]/.test(value);
  const hasDigit = /\d/.test(value);
  const hasSymbol = /[^A-Za-z0-9]/.test(value);
  const categories = [hasLower, hasUpper, hasDigit, hasSymbol].filter(Boolean).length;
  const common = COMMON_WEAK_WORDS.some((word) => lower.includes(word));
  const keyboard = KEYBOARD_PATTERNS.some((pattern) => lower.includes(pattern));
  const reasons = [];

  if (!value) {
    reasons.push("请输入密码。");
  }

  if (value.length > 0 && value.length < 8) {
    reasons.push("密码少于 8 位，按规则直接判为弱密码。");
  }

  if (common) {
    reasons.push("包含常见弱口令词，例如 student、admin、password。");
  }

  if (keyboard) {
    reasons.push("包含键盘连续模式，例如 qwerty、1234。");
  }

  if (hasRepeated(value)) {
    reasons.push("存在 3 个及以上连续重复字符。");
  }

  if (hasSequence(value)) {
    reasons.push("存在连续顺序字符，建议打散或替换。");
  }

  if (value.length >= 8 && categories < 3) {
    reasons.push("字符类型还不够丰富，建议混合大小写、数字和符号。");
  }

  return {
    categories,
    common,
    keyboard,
    hardWeak: value.length > 0 && (value.length < 8 || common),
    reasons
  };
}

function predictWithModel(password) {
  if (!state.model) {
    return heuristicPredict(password);
  }

  const tokens = extractFeatures(password);
  const unknownProbability = 1 / (state.model.vocabulary.length + 100);
  const scores = {};

  state.model.classes.forEach((label) => {
    let score = Math.log(state.model.priors[label]);

    tokens.forEach((token) => {
      const probability = state.model.likelihoods[label][token] || unknownProbability;
      score += Math.log(probability);
    });

    scores[label] = score;
  });

  return Object.keys(scores).reduce((best, label) => {
    return scores[label] > scores[best] ? label : best;
  }, state.model.classes[0]);
}

function heuristicPredict(password) {
  const value = String(password || "");
  const rules = getPasswordRules(value);

  if (!value || value.length < 8 || rules.common || rules.categories <= 1) {
    return "weak";
  }

  if (value.length >= 12 && rules.categories >= 3 && !rules.keyboard) {
    return "strong";
  }

  return "medium";
}

function evaluatePassword(password) {
  const value = String(password || "");
  const rules = getPasswordRules(value);
  let label = predictWithModel(value);

  if (!value) {
    label = "";
  } else if (rules.hardWeak) {
    label = "weak";
  } else if (label === "strong" && value.length < 12 && hasSequence(value)) {
    label = "medium";
  } else if (value.length >= 12 && rules.categories >= 4 && !rules.common && !rules.keyboard && !hasRepeated(value)) {
    label = "strong";
  }

  return {
    label,
    reasons: rules.reasons
  };
}

function isValidEmailFormat(email) {
  return /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/.test(email);
}

function extractDomain(email) {
  const parts = String(email || "").trim().toLowerCase().split("@");
  return parts.length === 2 ? parts[1] : "";
}

function isRiskyDomain(domain) {
  if (!domain) {
    return false;
  }

  const pieces = domain.split(".");

  for (let index = 0; index < pieces.length - 1; index += 1) {
    const candidate = pieces.slice(index).join(".");

    if (state.tempEmailDomains.has(candidate)) {
      return true;
    }
  }

  return false;
}

function setFieldState(input, hint, status, message) {
  input.classList.remove("valid", "warning", "invalid");
  hint.classList.remove("success", "warning", "error");

  if (status) {
    input.classList.add(status);
  }

  if (status === "valid") {
    hint.classList.add("success");
  } else if (status === "warning") {
    hint.classList.add("warning");
  } else if (status === "invalid") {
    hint.classList.add("error");
  }

  hint.textContent = message;
}

function setBadge(badge, tone, text) {
  if (!badge) {
    return;
  }

  badge.classList.remove("muted", "success", "warning", "danger");
  badge.classList.add(tone);
  badge.textContent = text;
}

function validateUsername() {
  const value = fields.username.value.trim();

  if (!value) {
    setFieldState(fields.username, fields.usernameHint, "", "请输入至少 2 个字符。");
    return false;
  }

  if (value.length < 2) {
    setFieldState(fields.username, fields.usernameHint, "invalid", "用户名太短，请至少输入 2 个字符。");
    return false;
  }

  setFieldState(fields.username, fields.usernameHint, "valid", "用户名格式可用。");
  return true;
}

function validateEmail() {
  const value = fields.email.value.trim();
  const domain = extractDomain(value);

  if (!value) {
    state.emailResult = {
      ok: false,
      risky: false,
      message: "会自动检查邮箱格式与一次性邮箱域名。"
    };
    setFieldState(fields.email, fields.emailHint, "", state.emailResult.message);
    setBadge(fields.emailBadge, "muted", "待输入");
    return false;
  }

  if (!isValidEmailFormat(value)) {
    state.emailResult = {
      ok: false,
      risky: false,
      message: "邮箱格式错误，请检查 @ 和域名结构。"
    };
    setFieldState(fields.email, fields.emailHint, "invalid", state.emailResult.message);
    setBadge(fields.emailBadge, "danger", "格式错误");
    return false;
  }

  if (isRiskyDomain(domain)) {
    state.emailResult = {
      ok: false,
      risky: true,
      message: `检测到高风险临时邮箱域名：${domain}。`
    };
    setFieldState(fields.email, fields.emailHint, "invalid", state.emailResult.message);
    setBadge(fields.emailBadge, "danger", "高风险邮箱");
    return false;
  }

  state.emailResult = {
    ok: true,
    risky: false,
    message: `邮箱格式正确，域名 ${domain} 未命中风险库。`
  };
  setFieldState(fields.email, fields.emailHint, "valid", state.emailResult.message);
  setBadge(fields.emailBadge, "success", "安全邮箱");
  return true;
}

function validatePassword() {
  const value = fields.password.value;
  const result = evaluatePassword(value);
  state.passwordResult = result;

  fields.strengthBar.className = "";

  if (!value) {
    setFieldState(fields.password, fields.passwordHint, "", "建议至少 8 位，并混合大小写、数字和符号。");
    setBadge(fields.passwordBadge, "muted", "待输入");
    updateAdvice();
    return false;
  }

  fields.strengthBar.classList.add(result.label);

  if (result.label === "weak") {
    setFieldState(fields.password, fields.passwordHint, "invalid", `${CLASS_TEXT[result.label]}：请增加长度并避免常见弱口令。`);
    setBadge(fields.passwordBadge, "danger", "弱");
  } else if (result.label === "medium") {
    setFieldState(fields.password, fields.passwordHint, "warning", `${CLASS_TEXT[result.label]}：可以使用，但建议加入更多字符类型。`);
    setBadge(fields.passwordBadge, "warning", "中等");
  } else {
    setFieldState(fields.password, fields.passwordHint, "valid", `${CLASS_TEXT[result.label]}：模型判断较安全。`);
    setBadge(fields.passwordBadge, "success", "强");
  }

  validateConfirmPassword();
  updateAdvice();
  return result.label !== "weak";
}

function validateConfirmPassword() {
  const password = fields.password.value;
  const confirm = fields.confirmPassword.value;

  if (!confirm) {
    setFieldState(fields.confirmPassword, fields.confirmHint, "", "请再次输入同一密码。");
    return false;
  }

  if (password !== confirm) {
    setFieldState(fields.confirmPassword, fields.confirmHint, "invalid", "两次密码不一致，提交会被拦截。");
    return false;
  }

  setFieldState(fields.confirmPassword, fields.confirmHint, "valid", "两次密码一致。");
  return true;
}

function updateAdvice() {
  const items = [];
  const passwordValue = fields.password.value;

  if (state.emailResult.risky) {
    items.push("邮箱命中临时邮箱域名库，请换用长期有效邮箱。");
  } else if (state.emailResult.ok) {
    items.push("邮箱格式与域名规则检查通过。");
  }

  if (passwordValue && state.passwordResult.label) {
    items.push(`朴素贝叶斯预测结果：${CLASS_TEXT[state.passwordResult.label]}。`);
    items.push(`提取到的特征：${extractFeatures(passwordValue).join("，")}。`);
  }

  state.passwordResult.reasons.forEach((reason) => items.push(reason));

  if (passwordValue && state.passwordResult.label === "strong" && !state.emailResult.risky) {
    items.push("密码复杂度表现不错，继续确认密码即可提交。");
  }

  if (!items.length) {
    items.push("填写表单后，这里会展示模型和规则引擎给出的建议。");
  }

  fields.adviceList.replaceChildren(
    ...items.map((item) => {
      const li = document.createElement("li");
      li.textContent = item;
      return li;
    })
  );
}

function validateAll() {
  const usernameOk = validateUsername();
  const emailOk = validateEmail();
  const passwordOk = validatePassword();
  const confirmOk = validateConfirmPassword();

  updateAdvice();

  return usernameOk && emailOk && passwordOk && confirmOk;
}

function setResourceStatus(kind, ok, message) {
  const dot = kind === "model" ? fields.modelDot : fields.emailDot;
  const label = kind === "model" ? fields.modelStatus : fields.emailStatus;

  dot.classList.remove("ready", "error");
  dot.classList.add(ok ? "ready" : "error");
  label.textContent = message;
}

async function loadModel() {
  try {
    const response = await fetch("./model/password_nb_model.json");

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }

    state.model = await response.json();
    setResourceStatus("model", true, `已加载 ${state.model.classes.length} 类密码模型。`);
  } catch (error) {
    state.model = null;
    setResourceStatus("model", false, "模型加载失败，已启用规则兜底。请用 Live Server 打开页面。");
  }
}

async function loadEmailDomains() {
  try {
    const response = await fetch("./data/email_data.txt");

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }

    const text = await response.text();
    const domains = text
      .split(/\r?\n/)
      .map((line) => line.trim().toLowerCase())
      .filter((line) => line && !line.startsWith("#"));

    state.tempEmailDomains = new Set(domains);
    setResourceStatus("email", true, `已加载 ${state.tempEmailDomains.size} 条临时邮箱域名。`);
  } catch (error) {
    state.tempEmailDomains = new Set(["mailinator.com", "10minutemail.com", "yopmail.com", "guerrillamail.com"]);
    setResourceStatus("email", false, "规则库加载失败，已启用内置演示域名。");
  }
}

function fillSample(type) {
  const samples = {
    weak: {
      password: "123456",
      confirmPassword: "123456"
    },
    medium: {
      password: "kzde5577",
      confirmPassword: "kzde5577"
    },
    strong: {
      password: "AVYq1lDE4MgAZfNt",
      confirmPassword: "AVYq1lDE4MgAZfNt"
    },
    riskyEmail: {
      email: "abc@mailinator.com"
    }
  };

  const sample = samples[type];

  if (!sample) {
    return;
  }

  Object.entries(sample).forEach(([key, value]) => {
    fields[key].value = value;
  });

  validateAll();
}

function bindEvents() {
  fields.username.addEventListener("input", () => {
    validateUsername();
    fields.submitMessage.textContent = "";
  });

  fields.email.addEventListener("input", () => {
    validateEmail();
    updateAdvice();
    fields.submitMessage.textContent = "";
  });

  fields.password.addEventListener("input", () => {
    validatePassword();
    fields.submitMessage.textContent = "";
  });

  fields.confirmPassword.addEventListener("input", () => {
    validateConfirmPassword();
    fields.submitMessage.textContent = "";
  });

  fields.togglePassword.addEventListener("click", () => {
    const isHidden = fields.password.type === "password";
    fields.password.type = isHidden ? "text" : "password";
    fields.confirmPassword.type = isHidden ? "text" : "password";
    fields.togglePassword.textContent = isHidden ? "隐藏" : "显示";
  });

  document.querySelectorAll("[data-sample]").forEach((button) => {
    button.addEventListener("click", () => fillSample(button.dataset.sample));
  });

  fields.form.addEventListener("submit", (event) => {
    event.preventDefault();
    fields.submitMessage.classList.remove("success", "error");

    if (!validateAll()) {
      fields.submitMessage.classList.add("error");
      fields.submitMessage.textContent = "提交已拦截：请先修正红色提示项。";
      return;
    }

    fields.submitMessage.classList.add("success");
    fields.submitMessage.textContent = "验证通过：表单可以提交。";
  });
}

async function init() {
  bindEvents();
  await Promise.all([loadModel(), loadEmailDomains()]);
  validateAll();
}

init();
