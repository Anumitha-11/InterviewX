document.addEventListener('DOMContentLoaded', () => {
  const API_BASE_URL = "http://localhost:8000/api";

  // Auth DOM Elements
  const signinModal = document.getElementById('signin-modal');
  const registerModal = document.getElementById('register-modal');
  const navSigninBtn = document.getElementById('nav-signin-btn');
  const navRegisterBtn = document.getElementById('nav-register-btn');
  const navLogoutBtn = document.getElementById('nav-logout-btn');
  const userGreeting = document.getElementById('user-greeting');
  const publicNavLinks = document.getElementById('public-nav-links');
  
  const signinClose = document.getElementById('signin-close');
  const registerClose = document.getElementById('register-close');
  const toRegister = document.getElementById('to-register');
  const toSignin = document.getElementById('to-signin');
  
  const signinForm = document.getElementById('signin-form');
  const registerForm = document.getElementById('register-form');
  const signinError = document.getElementById('signin-error');
  const registerError = document.getElementById('register-error');

  // Containers
  const landingContainer = document.getElementById('landing-container');
  const appContainer = document.getElementById('app-container');

  // Active state
  let activeInterviewId = null;

  // API Request Helper
  async function apiRequest(endpoint, options = {}) {
    const token = localStorage.getItem("token");
    const headers = {
      "Content-Type": "application/json",
      ...(options.headers || {})
    };
    if (token) {
      headers["Authorization"] = `Bearer ${token}`;
    }
    
    const response = await fetch(`${API_BASE_URL}${endpoint}`, {
      ...options,
      headers
    });
    
    if (response.status === 401) {
      localStorage.removeItem("token");
      localStorage.removeItem("name");
      updateAuthState();
      throw new Error("Session expired. Please sign in again.");
    }
    
    if (!response.ok) {
      const errData = await response.json().catch(() => ({}));
      throw new Error(errData.detail || "API Request failed");
    }
    return response.json();
  }

  // Authentication State Handler
  function updateAuthState() {
    const token = localStorage.getItem("token");
    if (token) {
      // Authenticated view
      if (navSigninBtn) navSigninBtn.style.display = "none";
      if (navRegisterBtn) navRegisterBtn.style.display = "none";
      if (navLogoutBtn) navLogoutBtn.style.display = "block";
      if (userGreeting) {
        userGreeting.style.display = "block";
        const cachedName = localStorage.getItem("name") || "Developer";
        userGreeting.textContent = `[ ${cachedName.toUpperCase()} ]`;
      }
      if (publicNavLinks) publicNavLinks.style.display = "none";
      
      landingContainer.style.display = "none";
      appContainer.style.display = "grid";
      
      // Load active dashboard
      loadDashboardData();
      loadProfileIntoForm();
    } else {
      // Public landing page view
      if (navSigninBtn) navSigninBtn.style.display = "block";
      if (navRegisterBtn) navRegisterBtn.style.display = "block";
      if (navLogoutBtn) navLogoutBtn.style.display = "none";
      if (userGreeting) userGreeting.style.display = "none";
      if (publicNavLinks) publicNavLinks.style.display = "flex";
      
      landingContainer.style.display = "block";
      appContainer.style.display = "none";
      
      // Reset simulator views
      resetSimulatorState();
    }
  }

  // Modal open/close listeners
  if (navSigninBtn) navSigninBtn.addEventListener('click', () => { signinModal.style.display = 'flex'; signinError.style.display = 'none'; });
  if (navRegisterBtn) navRegisterBtn.addEventListener('click', () => { registerModal.style.display = 'flex'; registerError.style.display = 'none'; });
  if (signinClose) signinClose.addEventListener('click', () => signinModal.style.display = 'none');
  if (registerClose) registerClose.addEventListener('click', () => registerModal.style.display = 'none');
  
  if (toRegister) {
    toRegister.addEventListener('click', (e) => {
      e.preventDefault();
      signinModal.style.display = 'none';
      registerModal.style.display = 'flex';
      registerError.style.display = 'none';
    });
  }
  
  if (toSignin) {
    toSignin.addEventListener('click', (e) => {
      e.preventDefault();
      registerModal.style.display = 'none';
      signinModal.style.display = 'flex';
      signinError.style.display = 'none';
    });
  }

  if (navLogoutBtn) {
    navLogoutBtn.addEventListener('click', () => {
      localStorage.removeItem("token");
      localStorage.removeItem("name");
      activeInterviewId = null;
      updateAuthState();
    });
  }

  // Auth Forms Submission
  if (registerForm) {
    registerForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      registerError.style.display = 'none';
      const name = document.getElementById('register-name').value;
      const email = document.getElementById('register-email').value;
      const password = document.getElementById('register-password').value;
      
      try {
        await apiRequest("/auth/register", {
          method: "POST",
          body: JSON.stringify({ name, email, password })
        });
        registerModal.style.display = 'none';
        signinModal.style.display = 'flex';
        // Auto fill email for convienence
        document.getElementById('signin-email').value = email;
        alert("Registration successful. Please sign in.");
      } catch (err) {
        registerError.textContent = err.message;
        registerError.style.display = 'block';
      }
    });
  }

  if (signinForm) {
    signinForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      signinError.style.display = 'none';
      const email = document.getElementById('signin-email').value;
      const password = document.getElementById('signin-password').value;
      
      try {
        const tokenData = await apiRequest("/auth/login", {
          method: "POST",
          body: JSON.stringify({ email, password })
        });
        localStorage.setItem("token", tokenData.access_token);
        
        // Retrieve name
        const userMe = await apiRequest("/users/me");
        localStorage.setItem("name", userMe.profile.name);
        
        signinModal.style.display = 'none';
        updateAuthState();
      } catch (err) {
        signinError.textContent = err.message;
        signinError.style.display = 'block';
      }
    });
  }

  // Workspace Sidebar Tab Switcher
  const sidebarTabs = document.querySelectorAll('.sidebar-tab-btn');
  const tabPanels = document.querySelectorAll('.dashboard-tab-panel');

  sidebarTabs.forEach(tab => {
    tab.addEventListener('click', () => {
      sidebarTabs.forEach(t => t.classList.remove('active'));
      tabPanels.forEach(p => p.classList.remove('active'));
      
      tab.classList.add('active');
      const tabId = tab.dataset.tab;
      const targetPanel = document.getElementById(`tab-${tabId}`);
      if (targetPanel) {
        targetPanel.classList.add('active');
      }
    });
  });

  // ----------------------------------------------------
  // DASHBOARD LOADING & UPDATING
  // ----------------------------------------------------
  async function loadDashboardData() {
    try {
      const data = await apiRequest("/progress/dashboard");
      
      // Candidate Header info
      document.getElementById('dash-profile-name').textContent = localStorage.getItem("name") || "Developer";
      
      let roleText = "Configure target role in Settings";
      if (data.target_role) {
        roleText = `Target: ${data.target_role}`;
        if (data.target_company) {
          roleText += ` at ${data.target_company}`;
        }
      }
      document.getElementById('dash-profile-role').textContent = roleText;
      
      const resumeStatusText = data.resume_uploaded ? `Resume: ${data.resume_filename}` : "Resume: No resume uploaded";
      document.getElementById('dash-profile-company').textContent = resumeStatusText;
      
      // Readiness Metric & Streak
      const readinessVal = document.getElementById('dash-readiness-val');
      const streakDesc = document.getElementById('dash-streak-desc');
      
      if (data.overall_readiness === 0) {
        readinessVal.textContent = "Not assessed";
        streakDesc.textContent = "Complete your first mock interview to generate a readiness score.";
      } else {
        readinessVal.textContent = `${data.overall_readiness}%`;
        streakDesc.textContent = `Daily streak: ${data.daily_streak} days. Practice run activity shows conceptual strength fit. Keep preparation loops going.`;
      }
      
      // Skills fit progress bars
      const skillsContainer = document.getElementById('dash-skills-container');
      skillsContainer.innerHTML = '';
      if (Object.keys(data.skills_fit).length === 0) {
        skillsContainer.innerHTML = `
          <p style="font-size: 0.85rem; color: var(--text-secondary);">No skill analysis yet. Upload your resume to unlock this signal.</p>
        `;
      } else {
        Object.entries(data.skills_fit).forEach(([skill, matchScore]) => {
          const row = document.createElement('div');
          row.className = 'skill-row';
          
          if (typeof matchScore === 'number') {
            row.innerHTML = `
              <div class="skill-info">
                <span class="skill-name">${skill}</span>
                <span class="skill-percentage">${matchScore}% Match</span>
              </div>
              <div class="skill-bar-wrap">
                <div class="skill-bar-fill" style="width: ${matchScore}%"></div>
              </div>
            `;
          } else {
            row.innerHTML = `
              <div class="skill-info" style="margin-bottom: 0;">
                <span class="skill-name">${skill}</span>
                <span class="skill-percentage" style="color: var(--text-secondary); text-transform: uppercase; font-size: 0.7rem; letter-spacing: 0.05em;">● ${matchScore}</span>
              </div>
            `;
          }
          skillsContainer.appendChild(row);
        });
      }

      // Weak / Strong areas lists
      const strongList = document.getElementById('dash-strong-list');
      strongList.innerHTML = '';
      if (data.strong_areas.length === 0) {
        const li = document.createElement('li');
        li.textContent = "No strengths identified yet";
        li.style.color = "var(--text-secondary)";
        strongList.appendChild(li);
      } else {
        data.strong_areas.forEach(area => {
          const li = document.createElement('li');
          li.textContent = `✓ ${area}`;
          strongList.appendChild(li);
        });
      }

      const weakList = document.getElementById('dash-weak-list');
      weakList.innerHTML = '';
      if (data.weak_areas.length === 0) {
        const li = document.createElement('li');
        li.textContent = "No gaps identified yet";
        li.style.color = "var(--text-secondary)";
        weakList.appendChild(li);
      } else {
        data.weak_areas.forEach(area => {
          const li = document.createElement('li');
          li.textContent = `▲ ${area}`;
          weakList.appendChild(li);
        });
      }

      // Study Roadmap Path
      const roadmapContainer = document.getElementById('dash-roadmap-container');
      roadmapContainer.innerHTML = '';
      if (data.roadmap.length === 0) {
        roadmapContainer.innerHTML = `
          <p style="font-size: 0.85rem; color: var(--text-secondary);">Your preparation path will adapt as InterviewX learns your profile.</p>
        `;
      } else {
        data.roadmap.forEach(item => {
          const node = document.createElement('div');
          node.className = `journey-node ${item.status}`;
          
          let actionLabel = "Mark as Active";
          let nextStatus = "in_progress";
          if (item.status === 'in_progress') {
            actionLabel = "Mark as Completed";
            nextStatus = "completed";
          } else if (item.status === 'completed') {
            actionLabel = "Reopen topic";
            nextStatus = "pending";
          }
          
          node.innerHTML = `
            <div class="journey-node-header">
              <span class="journey-node-title">${item.topic_name}</span>
              <span class="journey-node-status">${item.status.replace('_', ' ')}</span>
            </div>
            <p class="journey-node-desc">${item.recommendations || 'Conceptual study focus.'}</p>
            <span class="action-status-btn" data-id="${item.id}" data-next-status="${nextStatus}">${actionLabel}</span>
          `;
          roadmapContainer.appendChild(node);
        });

        // Add event listeners to roadmap status toggle actions
        roadmapContainer.querySelectorAll('.action-status-btn').forEach(btn => {
          btn.addEventListener('click', async () => {
            const itemId = btn.dataset.id;
            const nextStatus = btn.dataset.nextStatus;
            try {
              await apiRequest(`/progress/roadmap/${itemId}?status=${nextStatus}`, {
                method: "PUT"
              });
              loadDashboardData(); // Refresh metrics
            } catch (err) {
              alert(`Roadmap update failed: ${err.message}`);
            }
          });
        });
      }

      // Recent Runs List
      const activityContainer = document.getElementById('dash-activity-container');
      activityContainer.innerHTML = '';
      if (data.recent_activity.length === 0) {
        activityContainer.innerHTML = `
          <p style="font-size: 0.85rem; color: var(--text-secondary);">No interview runs yet. Start your first mock interview.</p>
        `;
      } else {
        data.recent_activity.forEach(act => {
          const item = document.createElement('div');
          item.className = 'activity-item';
          item.innerHTML = `
            <div>
              <span class="activity-title">${act.title}</span>
              <p class="activity-desc">${act.description}</p>
            </div>
            <span class="activity-date">${act.date}</span>
          `;
          activityContainer.appendChild(item);
        });
      }

      // Resume workspace section persistence
      const uploadStatus = document.getElementById('resume-upload-status');
      const parsedResults = document.getElementById('parsed-resume-results');
      const parsedSkillsList = document.getElementById('parsed-skills-list');
      const parsedGapsList = document.getElementById('parsed-gaps-list');
      
      if (data.resume_uploaded) {
        if (uploadStatus) uploadStatus.textContent = `✓ Parsed successfully: ${data.resume_filename}`;
        if (parsedResults) {
          parsedResults.style.display = 'flex';
          parsedSkillsList.innerHTML = '';
          Object.keys(data.skills_fit).forEach(skill => {
            const span = document.createElement('span');
            span.textContent = skill;
            parsedSkillsList.appendChild(span);
          });
          
          parsedGapsList.innerHTML = '';
          if (data.weak_areas.length > 0) {
            data.weak_areas.forEach(gap => {
              const li = document.createElement('li');
              li.textContent = gap;
              parsedGapsList.appendChild(li);
            });
          } else {
            const li = document.createElement('li');
            li.textContent = "Your profile hasn't been scanned yet. Upload your resume to begin skill analysis.";
            parsedGapsList.appendChild(li);
          }
        }
      } else {
        if (uploadStatus) uploadStatus.textContent = "No PDF chosen (Required file format: PDF)";
        if (parsedResults) parsedResults.style.display = 'none';
      }

    } catch (err) {
      console.error("Dashboard metric load failure:", err);
    }
  }

  // ----------------------------------------------------
  // PROFILE INVENTORY GET/PUT
  // ----------------------------------------------------
  async function loadProfileIntoForm() {
    try {
      const user = await apiRequest("/users/me");
      const profile = user.profile;
      if (profile) {
        document.getElementById('prof-name').value = profile.name || '';
        document.getElementById('prof-role').value = profile.target_role || '';
        document.getElementById('prof-experience').value = profile.experience_level || 'Mid Level';
        document.getElementById('prof-company').value = profile.target_company || '';
        document.getElementById('prof-pref-type').value = profile.preferred_type || 'Mix';
        document.getElementById('prof-skills').value = (profile.skills || []).join(', ');
      }
    } catch (err) {
      console.error("Profile retrieval failure:", err);
    }
  }

  const profileSettingsForm = document.getElementById('profile-settings-form');
  const profileSaveStatus = document.getElementById('profile-save-status');
  if (profileSettingsForm) {
    profileSettingsForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      profileSaveStatus.style.display = 'none';
      
      const name = document.getElementById('prof-name').value;
      const target_role = document.getElementById('prof-role').value;
      const experience_level = document.getElementById('prof-experience').value;
      const target_company = document.getElementById('prof-company').value;
      const preferred_type = document.getElementById('prof-pref-type').value;
      const skillsInput = document.getElementById('prof-skills').value;
      const skills = skillsInput.split(',').map(s => s.trim()).filter(s => s.length > 0);
      
      try {
        await apiRequest("/users/profile", {
          method: "PUT",
          body: JSON.stringify({
            name, target_role, experience_level, target_company, preferred_type, skills
          })
        });
        localStorage.setItem("name", name);
        profileSaveStatus.style.display = 'block';
        setTimeout(() => { profileSaveStatus.style.display = 'none'; }, 3000);
        loadDashboardData();
      } catch (err) {
        alert(`Failed to save profile: ${err.message}`);
      }
    });
  }

  // ----------------------------------------------------
  // RESUME SCANNING & ANALYSIS
  // ----------------------------------------------------
  const fileInput = document.getElementById('resume-file-input');
  const uploadStatus = document.getElementById('resume-upload-status');
  const parsedResults = document.getElementById('parsed-resume-results');
  const parsedSkillsList = document.getElementById('parsed-skills-list');
  const parsedGapsList = document.getElementById('parsed-gaps-list');

  if (fileInput) {
    fileInput.addEventListener('change', async () => {
      const file = fileInput.files[0];
      if (!file) return;
      
      const formData = new FormData();
      formData.append("file", file);
      
      uploadStatus.textContent = "Ingesting and auditing resume PDF...";
      parsedResults.style.display = 'none';
      
      const token = localStorage.getItem("token");
      try {
        const response = await fetch(`${API_BASE_URL}/resume/upload`, {
          method: "POST",
          headers: {
            "Authorization": `Bearer ${token}`
          },
          body: formData
        });
        
        if (!response.ok) {
          const errData = await response.json().catch(() => ({}));
          throw new Error(errData.detail || "Ingestion audit failed");
        }
        
        const resumeData = await response.json();
        uploadStatus.textContent = `✓ Parsed successfully: ${file.name}`;
        
        // Show results
        parsedResults.style.display = 'flex';
        parsedSkillsList.innerHTML = '';
        resumeData.parsed_skills.forEach(skill => {
          const span = document.createElement('span');
          span.textContent = skill;
          parsedSkillsList.appendChild(span);
        });
        
        parsedGapsList.innerHTML = '';
        resumeData.weaknesses.forEach(gap => {
          const li = document.createElement('li');
          li.textContent = gap;
          parsedGapsList.appendChild(li);
        });
        
        // Refresh dashboard metrics
        loadDashboardData();
        loadProfileIntoForm();
      } catch (err) {
        uploadStatus.textContent = `Error: ${err.message}`;
      }
    });
  }

  // ----------------------------------------------------
  // CALM MOCK SIMULATOR EXPERIENCE
  // ----------------------------------------------------
  const mockLobby = document.getElementById('mock-lobby');
  const mockSandbox = document.getElementById('mock-sandbox');
  const mockEvaluation = document.getElementById('mock-evaluation');
  const mockReport = document.getElementById('mock-report');
  
  const startMockBtn = document.getElementById('start-mock-btn');
  const simInputText = document.getElementById('sim-input-text');
  const simSendBtn = document.getElementById('sim-send-btn');
  const simQuestionText = document.getElementById('sim-question-text');
  const simProgressCounter = document.getElementById('sim-progress-counter');
  const simLogConsole = document.getElementById('sim-log-console');
  const simMetaCategory = document.getElementById('sim-meta-category');
  const simMetaDifficulty = document.getElementById('sim-meta-difficulty');
  
  const evalNextBtn = document.getElementById('eval-next-btn');
  const reportCloseBtn = document.getElementById('report-close-btn');

  let currentEvaluationResponse = null;

  function appendLogLine(text, level = '') {
    const div = document.createElement('div');
    div.className = `log-line ${level}`;
    div.textContent = `${new Date().toLocaleTimeString()} ${text}`;
    simLogConsole.appendChild(div);
    simLogConsole.scrollTop = simLogConsole.scrollHeight;
  }

  function resetSimulatorState() {
    activeInterviewId = null;
    currentEvaluationResponse = null;
    mockLobby.style.display = "block";
    mockSandbox.style.display = "none";
    mockEvaluation.style.display = "none";
    mockReport.style.display = "none";
    simInputText.value = '';
    simInputText.disabled = false;
    simSendBtn.disabled = false;
    simLogConsole.innerHTML = '<div class="log-line">🤖 Console initialized.</div>';
  }

  if (startMockBtn) {
    startMockBtn.addEventListener('click', async () => {
      const roleOverride = document.getElementById('mock-config-role').value.trim();
      const companyOverride = document.getElementById('mock-config-company').value.trim();
      
      startMockBtn.disabled = true;
      startMockBtn.textContent = "Orchestrating agents...";
      
      try {
        const session = await apiRequest("/interview/start", {
          method: "POST",
          body: JSON.stringify({
            target_role: roleOverride || null,
            target_company: companyOverride || null
          })
        });
        
        activeInterviewId = session.id;
        
        // Transition views
        mockLobby.style.display = "none";
        mockSandbox.style.display = "grid";
        
        appendLogLine("✓ Start trigger received");
        appendLogLine("✓ Profile details loaded", "success");
        appendLogLine("✓ RAG context guidelines loaded", "success");
        appendLogLine("✓ Question Generated", "accent");
        
        // Question load
        const firstQ = session.questions[0];
        simQuestionText.textContent = firstQ.text;
        simProgressCounter.textContent = "Question 1 of 3";
        simMetaCategory.textContent = firstQ.category.toUpperCase();
        simMetaDifficulty.textContent = firstQ.difficulty.toUpperCase();
        simInputText.value = '';
        simInputText.disabled = false;
        simSendBtn.disabled = false;
        simInputText.focus();
        
      } catch (err) {
        alert(`Failed to start session: ${err.message}`);
        startMockBtn.disabled = false;
        startMockBtn.textContent = "Start Prep Run";
      }
    });
  }

  if (simSendBtn) {
    simSendBtn.addEventListener('click', async () => {
      const text = simInputText.value.trim();
      if (!text) return;
      
      simInputText.disabled = true;
      simSendBtn.disabled = true;
      
      appendLogLine("● Dispatching response to evaluation agent...");
      appendLogLine("○ Benchmarking correct definitions...");
      
      try {
        const response = await apiRequest(`/interview/${activeInterviewId}/answer`, {
          method: "POST",
          body: JSON.stringify({ text })
        });
        
        currentEvaluationResponse = response;
        appendLogLine("✓ Answer evaluated score calculated", "success");
        
        // Populate Evaluation Scorecard
        const grading = response.evaluation;
        document.getElementById('eval-score-overall').textContent = grading.overall_score.toFixed(1);
        document.getElementById('eval-score-tech').textContent = (grading.technical_score || grading.overall_score).toFixed(1);
        document.getElementById('eval-score-comm').textContent = (grading.communication_score || grading.overall_score).toFixed(1);
        document.getElementById('eval-score-relevance').textContent = (grading.relevance_score || grading.overall_score).toFixed(1);
        
        // Strengths & suggestions
        const strengthsList = document.getElementById('eval-strengths-list');
        strengthsList.innerHTML = '';
        (grading.strengths || ["Response met base correctness benchmarks."]).forEach(str => {
          const li = document.createElement('li');
          li.textContent = str;
          strengthsList.appendChild(li);
        });
        
        const suggestionsList = document.getElementById('eval-suggestions-list');
        suggestionsList.innerHTML = '';
        (grading.suggestions || ["Review vocabulary metrics to optimize layout alignment."]).forEach(sug => {
          const li = document.createElement('li');
          li.textContent = sug;
          suggestionsList.appendChild(li);
        });
        
        // Show evaluation panel
        mockSandbox.style.display = "none";
        mockEvaluation.style.display = "block";
        
        if (response.next_action === "finish_interview") {
          evalNextBtn.textContent = "Complete prep & View Report";
        } else {
          evalNextBtn.textContent = "Proceed to Next Question";
        }
        
      } catch (err) {
        alert(`Evaluation failed: ${err.message}`);
        simInputText.disabled = false;
        simSendBtn.disabled = false;
      }
    });
  }

  if (evalNextBtn) {
    evalNextBtn.addEventListener('click', async () => {
      if (!currentEvaluationResponse) return;
      
      const response = currentEvaluationResponse;
      mockEvaluation.style.display = "none";
      
      if (response.next_action === "ask_question") {
        // Proceed to next question sandbox
        mockSandbox.style.display = "grid";
        const nextQ = response.next_question;
        simQuestionText.textContent = nextQ.text;
        
        // Deduce question number
        const userAnswersCount = document.querySelectorAll('#tab-mock .sim-message.user').length + 1; // simulation logic
        const qCountText = `Question ${userAnswersCount + 1} of 3`;
        simProgressCounter.textContent = qCountText;
        
        simMetaCategory.textContent = nextQ.category.toUpperCase();
        simMetaDifficulty.textContent = nextQ.difficulty.toUpperCase();
        
        appendLogLine(`✓ Question generated: ${nextQ.category.toUpperCase()}`, "accent");
        
        simInputText.value = '';
        simInputText.disabled = false;
        simSendBtn.disabled = false;
        simInputText.focus();
        
      } else {
        // Retrieve Final Report
        try {
          const report = await apiRequest(`/interview/${activeInterviewId}/report`);
          
          document.getElementById('report-score-display').textContent = `${report.overall_score} / 10`;
          document.getElementById('report-feedback-summary').textContent = report.general_feedback;
          
          const repStrengths = document.getElementById('report-strengths-list');
          repStrengths.innerHTML = '';
          (report.strengths.length > 0 ? report.strengths : ["Structured communication style.", "Correct technical concept association."]).forEach(str => {
            const li = document.createElement('li');
            li.textContent = str;
            repStrengths.appendChild(li);
          });
          
          const repWeaknesses = document.getElementById('report-weaknesses-list');
          repWeaknesses.innerHTML = '';
          (report.weaknesses.length > 0 ? report.weaknesses : ["Distributed cache configuration detail.", "Advanced SQL window function execution."]).forEach(weak => {
            const li = document.createElement('li');
            li.textContent = weak;
            repWeaknesses.appendChild(li);
          });
          
          mockReport.style.display = "block";
          
        } catch (err) {
          alert(`Failed to fetch report: ${err.message}`);
          resetSimulatorState();
        }
      }
    });
  }

  if (reportCloseBtn) {
    reportCloseBtn.addEventListener('click', () => {
      resetSimulatorState();
      loadDashboardData();
      
      // Navigate sidebar back to dashboard tab
      sidebarTabs.forEach(t => t.classList.remove('active'));
      tabPanels.forEach(p => p.classList.remove('active'));
      
      const dashTab = document.querySelector('.sidebar-tab-btn[data-tab="dashboard"]');
      if (dashTab) dashTab.classList.add('active');
      
      const dashPanel = document.getElementById('tab-dashboard');
      if (dashPanel) dashPanel.classList.add('active');
    });
  }

  // Initial authentication check
  updateAuthState();
});
