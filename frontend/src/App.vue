<template>
  <main class="page-shell">
    <section class="hero">
      <div>
        <p class="eyebrow">AI Recruiting Copilot</p>
        <h1>&#x667A;&#x80FD;&#x7B80;&#x5386;&#x5206;&#x6790;&#x7CFB;&#x7EDF;</h1>
        <p class="hero-copy">
          &#x4E0A;&#x4F20; PDF &#x7B80;&#x5386;&#xFF0C;&#x81EA;&#x52A8;&#x63D0;&#x53D6;&#x5019;&#x9009;&#x4EBA;&#x4FE1;&#x606F;&#xFF0C;&#x5E76;&#x7ED3;&#x5408;&#x5C97;&#x4F4D;&#x63CF;&#x8FF0;&#x751F;&#x6210;&#x5339;&#x914D;&#x5EA6;&#x8BC4;&#x5206;&#x3002;
        </p>
      </div>
    </section>

    <section class="workspace">
      <div class="panel input-panel">
        <label class="field">
          <span>&#x4E0A;&#x4F20;&#x7B80;&#x5386; PDF</span>
          <input type="file" accept=".pdf,application/pdf" @change="handleFileChange" />
        </label>

        <label class="field">
          <span>&#x5C97;&#x4F4D;&#x9700;&#x6C42;&#x63CF;&#x8FF0;</span>
          <textarea
            v-model="jobDescription"
            rows="10"
            placeholder="&#x8BF7;&#x8F93;&#x5165;&#x5C97;&#x4F4D;&#x804C;&#x8D23;&#x3001;&#x6280;&#x80FD;&#x8981;&#x6C42;&#x3001;&#x7ECF;&#x9A8C;&#x8981;&#x6C42;&#x7B49;"
          />
        </label>

        <div class="actions">
          <button
            :disabled="loading || !selectedFile || !jobDescription.trim()"
            @click="analyzeResume"
          >
            {{
              loading && stage === "analyze"
                ? "\u5206\u6790\u4E2D..."
                : "\u4E00\u952E\u5206\u6790"
            }}
          </button>
          <button :disabled="loading || !selectedFile" @click="parseResume">
            {{
              loading && stage === "parse"
                ? "\u89E3\u6790\u4E2D..."
                : "1. \u89E3\u6790\u7B80\u5386"
            }}
          </button>
          <button
            class="secondary"
            :disabled="loading || !selectedFile || !jobDescription.trim()"
            @click="matchResume"
          >
            {{
              loading && stage === "match"
                ? "\u5339\u914D\u4E2D..."
                : "2. \u8BA1\u7B97\u5339\u914D\u5EA6"
            }}
          </button>
        </div>

        <p v-if="errorMessage" class="error-text">{{ errorMessage }}</p>
      </div>

      <div class="panel output-panel">
        <div class="panel-header">
          <h2>{{ panelTitle }}</h2>
          <span v-if="showCacheHit" class="cache-tag">
            Cache Hit
          </span>
        </div>

        <div v-if="!showParsedResult && !showMatchedResult" class="empty-state">
          &#x8BF7;&#x4E0A;&#x4F20; PDF &#x7B80;&#x5386;&#xFF0C;&#x7136;&#x540E;&#x70B9;&#x51FB;&#x201C;&#x4E00;&#x952E;&#x5206;&#x6790;&#x201D;&#x6216;&#x201C;&#x89E3;&#x6790;&#x7B80;&#x5386;&#x201D;&#x3002;
        </div>

        <template v-else>
          <template v-if="showParsedResult">
          <section class="result-section">
            <h3>&#x5019;&#x9009;&#x4EBA;&#x4FE1;&#x606F;</h3>
            <div class="info-grid">
              <div>
                <span>&#x59D3;&#x540D;</span>
                <strong>{{ parsedResume.extracted_info.basic_info.name || "-" }}</strong>
              </div>
              <div>
                <span>&#x7535;&#x8BDD;</span>
                <strong>{{ parsedResume.extracted_info.basic_info.phone || "-" }}</strong>
              </div>
              <div>
                <span>&#x90AE;&#x7BB1;</span>
                <strong>{{ parsedResume.extracted_info.basic_info.email || "-" }}</strong>
              </div>
              <div>
                <span>&#x5DE5;&#x4F5C;&#x5E74;&#x9650;</span>
                <strong>{{ parsedResume.extracted_info.years_of_experience || "-" }}</strong>
              </div>
              <div>
                <span>&#x6C42;&#x804C;&#x65B9;&#x5411;</span>
                <strong>{{ parsedResume.extracted_info.job_intention || "-" }}</strong>
              </div>
              <div>
                <span>&#x671F;&#x671B;&#x85AA;&#x8D44;</span>
                <strong>{{ parsedResume.extracted_info.expected_salary || "-" }}</strong>
              </div>
            </div>
          </section>

          <section class="result-section">
            <h3>&#x4E13;&#x4E1A;&#x6280;&#x80FD;</h3>
            <div class="chips">
              <span
                v-for="skill in parsedResume.extracted_info.skills"
                :key="skill"
                class="chip"
              >
                {{ skill }}
              </span>
              <span v-if="!parsedResume.extracted_info.skills.length" class="muted">
                &#x6682;&#x672A;&#x63D0;&#x53D6;&#x5230;&#x6280;&#x80FD;&#x6807;&#x7B7E;
              </span>
            </div>
          </section>

          <section class="result-section">
            <h3>&#x9879;&#x76EE;&#x7ECF;&#x5386;</h3>
            <div class="project-blocks">
              <div
                v-for="project in parsedResume.extracted_info.projects"
                :key="project"
                class="project-card"
              >
                {{ project }}
              </div>
              <div v-if="!parsedResume.extracted_info.projects.length" class="muted">
                &#x6682;&#x672A;&#x63D0;&#x53D6;&#x5230;&#x9879;&#x76EE;&#x6458;&#x8981;
              </div>
            </div>
          </section>

          <section class="result-section">
            <h3>&#x6559;&#x80B2;&#x4E0E;&#x6982;&#x8981;</h3>
            <ul class="project-list">
              <li
                v-for="education in parsedResume.extracted_info.education_background"
                :key="education"
              >
                {{ education }}
              </li>
              <li
                v-if="!parsedResume.extracted_info.education_background.length"
                class="muted"
              >
                &#x6682;&#x672A;&#x63D0;&#x53D6;&#x5230;&#x6559;&#x80B2;&#x80CC;&#x666F;
              </li>
            </ul>
            <p class="summary-text">
              {{ parsedResume.extracted_info.summary || "&#x6682;&#x65E0;&#x7B80;&#x5386;&#x6982;&#x8981;" }}
            </p>
          </section>
          </template>

          <section v-if="showMatchedResult" class="result-section">
            <h3>&#x5C97;&#x4F4D;&#x5339;&#x914D;&#x7ED3;&#x679C;</h3>
            <div class="score-card">
              <div>
                <span>&#x7EFC;&#x5408;&#x8BC4;&#x5206;</span>
                <strong>{{ matchedResume.match.overall_score }}</strong>
              </div>
              <div>
                <span>&#x5173;&#x952E;&#x8BCD;&#x5339;&#x914D;</span>
                <strong>{{ matchedResume.match.keyword_match_score }}</strong>
              </div>
              <div>
                <span>&#x7ECF;&#x9A8C;&#x76F8;&#x5173;&#x6027;</span>
                <strong>{{ matchedResume.match.experience_relevance_score }}</strong>
              </div>
            </div>

            <div class="analysis-grid">
              <div>
                <h4>&#x5339;&#x914D;&#x5173;&#x952E;&#x8BCD;</h4>
                <div class="chips">
                  <span
                    v-for="keyword in matchedResume.match.keywords"
                    :key="keyword"
                    class="chip chip-accent"
                  >
                    {{ keyword }}
                  </span>
                </div>
              </div>

              <div>
                <h4>&#x4F18;&#x52BF;</h4>
                <ul class="project-list">
                  <li v-for="item in matchedResume.match.strengths" :key="item">{{ item }}</li>
                </ul>
              </div>

              <div>
                <h4>&#x5F85;&#x8865;&#x5145;</h4>
                <ul class="project-list">
                  <li v-for="item in matchedResume.match.gaps" :key="item">{{ item }}</li>
                </ul>
              </div>
            </div>
          </section>
        </template>
      </div>
    </section>
  </main>
</template>

<script setup>
import { computed, ref } from "vue";

const API_BASE = import.meta.env.VITE_API_BASE || "http://test.52xinxin.top:8000/api/v1";

const selectedFile = ref(null);
const jobDescription = ref("");
const parsedResume = ref(null);
const matchedResume = ref(null);
const errorMessage = ref("");
const loading = ref(false);
const stage = ref("parse");

const showParsedResult = computed(() => {
  if (!parsedResume.value) return false;
  return stage.value === "parse" || stage.value === "analyze";
});

const showMatchedResult = computed(() => {
  if (!matchedResume.value) return false;
  return stage.value === "match" || stage.value === "analyze";
});

const showCacheHit = computed(() => {
  const parseCacheHit = showParsedResult.value && parsedResume.value?.cache_hit;
  const matchCacheHit = showMatchedResult.value && matchedResume.value?.cache_hit;
  return Boolean(parseCacheHit || matchCacheHit);
});

const panelTitle = computed(() => {
  if (stage.value === "parse") return "解析结果";
  if (stage.value === "match") return "匹配结果";
  return "分析结果";
});

function handleFileChange(event) {
  selectedFile.value = event.target.files?.[0] || null;
  parsedResume.value = null;
  matchedResume.value = null;
  errorMessage.value = "";
}

async function parseResume() {
  if (!selectedFile.value) return;
  loading.value = true;
  stage.value = "parse";
  errorMessage.value = "";

  try {
    const formData = new FormData();
    formData.append("file", selectedFile.value);
    const response = await fetch(`${API_BASE}/resumes/parse`, {
      method: "POST",
      body: formData,
    });
    const data = await response.json();
    if (!response.ok) {
      throw new Error(data.detail || "\u7B80\u5386\u89E3\u6790\u5931\u8D25");
    }
    parsedResume.value = data;
    matchedResume.value = null;
  } catch (error) {
    errorMessage.value = error.message || "\u7B80\u5386\u89E3\u6790\u5931\u8D25";
  } finally {
    loading.value = false;
  }
}

async function analyzeResume() {
  if (!selectedFile.value || !jobDescription.value.trim()) return;
  loading.value = true;
  stage.value = "analyze";
  errorMessage.value = "";

  try {
    const formData = new FormData();
    formData.append("file", selectedFile.value);
    formData.append("job_description", jobDescription.value);

    const response = await fetch(`${API_BASE}/resumes/analyze`, {
      method: "POST",
      body: formData,
    });
    const data = await response.json();
    if (!response.ok) {
      throw new Error(data.detail || "\u7B80\u5386\u5206\u6790\u5931\u8D25");
    }
    parsedResume.value = {
      file_name: data.file_name,
      text_length: data.text_length,
      cleaned_text: data.cleaned_text,
      extracted_info: data.extracted_info,
      cache_hit: data.cache_hit,
    };
    matchedResume.value = {
      job_description: data.job_description,
      extracted_info: data.extracted_info,
      match: data.match,
      cleaned_text: data.cleaned_text,
      cache_hit: data.cache_hit,
    };
  } catch (error) {
    errorMessage.value = error.message || "\u7B80\u5386\u5206\u6790\u5931\u8D25";
  } finally {
    loading.value = false;
  }
}

async function matchResume() {
  if (!selectedFile.value || !jobDescription.value.trim()) return;
  loading.value = true;
  stage.value = "match";
  errorMessage.value = "";

  try {
    const formData = new FormData();
    formData.append("file", selectedFile.value);
    formData.append("job_description", jobDescription.value);
    const response = await fetch(`${API_BASE}/resumes/match`, {
      method: "POST",
      body: formData,
    });
    const data = await response.json();
    if (!response.ok) {
      throw new Error(data.detail || "\u5C97\u4F4D\u5339\u914D\u5931\u8D25");
    }
    parsedResume.value = null;
    matchedResume.value = data;
  } catch (error) {
    errorMessage.value = error.message || "\u5C97\u4F4D\u5339\u914D\u5931\u8D25";
  } finally {
    loading.value = false;
  }
}
</script>
