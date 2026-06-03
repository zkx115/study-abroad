/**
 * Admission Advisor - JavaScript version (ported from Python)
 * Runs entirely client-side, no backend needed.
 */

const Advisor = {
  // ─── 默认权重 ───────────────────────
  DEFAULT_WEIGHTS: {
    gpa: 0.28, language: 0.17, gre: 0.12, background: 0.15,
    prerequisite: 0.15, extra: 0.06, competitiveness: 0.07
  },

  // ─── 过滤 ───────────────────────────
  filterPrograms(programs, student) {
    const budget = student.budget?.total_usd || 0;
    const safetyPref = student.safety_preference || 'medium';
    const gpa = student.gpa || 0;
    const minRank = student.min_rank || 0;
    const exclude = new Set(student.exclude_universities || []);

    return programs.filter(p => {
      // 排除列表
      if (exclude.has(p.u)) return false;

      // 排名过滤
      const rank = parseInt(p.r) || 99;
      if (minRank > 0 && rank > minRank) return false;

      // 安全检查（默认 7.5）
      const safety = parseFloat(p.sa) || 7.5;
      if (safetyPref === 'high' && safety < 7.0) return false;
      if (safetyPref === 'medium' && safety < 5.0) return false;

      // GPA 硬门槛
      const hardGpaCutoff = p.c === 'United States' ? 2.8 : 2.5;
      if (gpa < hardGpaCutoff) return false;

      // 预算检查
      const tuition = parseFloat(p.tu) || 0;
      const living = parseFloat(p.lv) || 0;
      const studyLen = parseFloat(p.sl) || 2;
      const totalCost = (tuition + living) * studyLen;
      const budgetMult = rank <= 10 ? 1.7 : 1.5;
      const budgetLimit = budget > 0 ? budget * budgetMult : Infinity;
      if (totalCost > budgetLimit) return false;

      // 附加字段
      p._totalCost = totalCost;
      p._tuition = tuition;
      p._living = living;
      p._safety = safety;
      p._studyLen = studyLen;
      p._rank = rank;
      return true;
    });
  },

  // ─── 评分 ───────────────────────────
  normalizeGPA(studentGpa, minGpa) {
    if (!minGpa || minGpa === 0) return 10;
    const ratio = studentGpa / minGpa;
    return Math.min(ratio * 10, 10);
  },

  normalizeLanguage(studentLang, program) {
    const langType = studentLang?.type || 'IELTS';
    const score = studentLang?.score || 0;
    let minVal;
    if (langType === 'TOEFL') minVal = parseFloat(program.f) || 90;
    else minVal = parseFloat(program.i) || 6.5;
    if (!minVal || minVal === 0) return 10;
    let ratio = score / minVal;
    if (ratio < 1.0) ratio *= 0.85;
    return Math.min(ratio * 10, 10);
  },

  normalizeGRE(greScore, requireGre) {
    if (greScore === null || greScore === undefined) {
      if (requireGre === 'optional') return 7.5;
      if (requireGre === 'yes' || requireGre === 'required') return 2.5;
      return 5.0;
    }
    return (greScore / 340) * 10;
  },

  normalizeExtra(program, student) {
    const safety = program._safety / 10 * 10;
    const climatePref = student.climate_preference || 'no_preference';
    const climateScore = climatePref === 'no_preference' ? 7.5 : 10;
    const visaFriendly = student.visa_friendly_required || false;
    const pwv = parseInt(program.vw) || 12;
    const visaScore = visaFriendly ? (pwv >= 36 ? 10 : pwv >= 24 ? 7.5 : 5.0) : 7.5;
    return (safety + climateScore + visaScore) / 3;
  },

  normalizeCompetitiveness(program) {
    const admitRate = parseFloat(program.ar) || 30;
    if (admitRate <= 3) return 2.0;
    if (admitRate <= 5) return 3.5;
    if (admitRate <= 10) return 5.0;
    if (admitRate <= 15) return 6.5;
    if (admitRate <= 20) return 7.5;
    if (admitRate <= 30) return 8.5;
    if (admitRate <= 45) return 9.5;
    return 10.0;
  },

  matchPrerequisites(requiredList, completedList) {
    const required = requiredList.filter(Boolean);
    const completed = completedList.filter(Boolean);
    if (!required.length) return { matched: 0, details: [], missing: [] };
    const matchedDetails = [];
    const missing = [];
    let matched = 0;
    for (const req of required) {
      const reqLower = req.toLowerCase();
      const reqWords = reqLower.replace(/[&/]/g, ' ').split(/\s+/).filter(w => w.length > 3);
      const reqBigWords = reqWords.filter(w => w.length > 5);
      let found = false;
      for (const done of completed) {
        const doneLower = done.toLowerCase();
        const bigMatch = reqBigWords.some(kw => doneLower.includes(kw));
        const kwMatches = reqWords.filter(kw => doneLower.includes(kw)).length;
        if (bigMatch || kwMatches >= 2) {
          matched++;
          matchedDetails.push({ required: req, matchedWith: done });
          found = true;
          break;
        }
      }
      if (!found) missing.push(req);
    }
    return { matched, details: matchedDetails, missing };
  },

  normalizePrerequisites(program, student) {
    const prereqStr = program.pr || '';
    if (!prereqStr) return 7.5;
    const required = prereqStr.split(';').map(c => c.trim()).filter(Boolean);
    const completed = student.completed_prerequisites || [];
    if (!required.length) return 7.5;
    const { matched } = this.matchPrerequisites(required, completed);
    const ratio = matched / required.length;
    return Math.min(ratio * 10, 10);
  },

  scoreBackground(student) {
    const bg = student.soft_background || {};
    const research = bg.research || [];
    const work = bg.work_experience || [];
    let score = 5.0;
    score += research.length * 0.8;
    score += work.length * 0.6;
    if (work.some(w => w.toLowerCase().includes('internship'))) score += 0.5;
    return Math.min(score, 10.0);
  },

  getWeights(student) {
    const weights = { ...this.DEFAULT_WEIGHTS };
    const studentWeights = student.weight_preferences || {};
    const hasCustom = Object.keys(studentWeights).length > 0;
    if (hasCustom) {
      let total = Object.values(studentWeights).reduce((a, b) => a + b, 0);
      if (total > 0) {
        for (const k of Object.keys(weights)) {
          if (k in studentWeights)
            weights[k] = weights[k] * 0.5 + (studentWeights[k] / total) * 0.5;
        }
      }
    }
    const career = student.career_goal || '';
    const visaFriendly = student.visa_friendly_required || false;
    if (career === 'stay_abroad' && visaFriendly) {
      if (weights.extra !== undefined) {
        weights.extra = Math.min(weights.extra * 2, 0.25);
        const total = Object.values(weights).reduce((a, b) => a + b, 0);
        for (const k of Object.keys(weights)) {
          if (k !== 'extra') weights[k] *= (1 - weights.extra) / (total - weights.extra);
        }
      }
    } else if (career === 'startup') {
      weights.gpa *= 0.8;
      weights.background *= 1.2;
      const total = Object.values(weights).reduce((a, b) => a + b, 0);
      for (const k of Object.keys(weights)) weights[k] /= total;
    }
    // 归一化
    const total = Object.values(weights).reduce((a, b) => a + b, 0);
    for (const k of Object.keys(weights)) weights[k] = Math.round((weights[k] / total) * 10000) / 10000;
    return weights;
  },

  // ─── 评分+分层 ─────────────────────
  scoreAndClassify(programs, student, weights) {
    if (!weights) weights = this.getWeights(student);
    const gpa = student.gpa || 0;
    const lang = student.language || {};
    const gre = student.gre;
    const bgScore = this.scoreBackground(student);

    const scored = programs.map(p => {
      const gpaNorm = this.normalizeGPA(gpa, parseFloat(p.g) || 3.0);
      const langNorm = this.normalizeLanguage(lang, p);
      const greNorm = this.normalizeGRE(gre, p.gr || '');
      const prereqNorm = this.normalizePrerequisites(p, student);
      const extraNorm = this.normalizeExtra(p, student);
      const compNorm = this.normalizeCompetitiveness(p);

      const match = weights.gpa * gpaNorm
        + weights.language * langNorm
        + weights.gre * greNorm
        + weights.background * bgScore
        + weights.prerequisite * prereqNorm
        + weights.extra * extraNorm
        + (weights.competitiveness || 0) * compNorm;

      const level = match >= 9.0 ? 'safety' : match >= 6.0 ? 'match' : match >= 4.0 ? 'reach' : 'lottery';

      return {
        ...p,
        _matchScore: Math.round(match * 10) / 10,
        _feasibilityLevel: level,
        _bgScore: Math.round(bgScore * 10) / 10,
      };
    });

    scored.sort((a, b) => b._matchScore - a._matchScore);
    return scored;
  },

  // ─── 多样化选择 ─────────────────────
  selectDiverse(scored, student) {
    if (!scored.length) return [];
    const targetUni = student.target_university;
    const targetMajor = student.target_major;

    let pool = scored;
    if (targetUni) pool = pool.filter(p => p.u === targetUni);
    if (targetMajor) pool = pool.filter(p => p.m === targetMajor);
    if (!pool.length) return [];

    const usedCountries = {};
    const levelsCollected = { safety: 0, match: 0, reach: 0, lottery: 0 };
    const phase1 = [];

    for (const p of pool) {
      const level = p._feasibilityLevel;
      const country = p.c;
      if (levelsCollected[level] >= 2) continue;
      if ((usedCountries[country] || 0) >= 2) continue;
      phase1.push(p);
      levelsCollected[level]++;
      usedCountries[country] = (usedCountries[country] || 0) + 1;
      if (phase1.length >= 5) break;
    }

    if (phase1.length < 3) {
      for (const p of pool) {
        if (phase1.includes(p)) continue;
        const country = p.c;
        if ((usedCountries[country] || 0) >= 3) continue;
        phase1.push(p);
        usedCountries[country] = (usedCountries[country] || 0) + 1;
        if (phase1.length >= 5) break;
      }
    }

    // 冲刺校
    const aspirational = pool.filter(p =>
      !phase1.includes(p) && p._rank <= 5 && p._matchScore >= 4.0
    );
    aspirational.sort((a, b) => a._rank - b._rank);
    for (const p of aspirational) {
      if (phase1.filter(x => x.u === p.u).length >= 2) continue;
      if (phase1.length >= 9) break;
      phase1.push(p);
    }

    return phase1;
  },

  // ─── 主入口 ─────────────────────────
  recommend(programs, student) {
    console.log('Advisor starting recommendation...');
    const filtered = this.filterPrograms(programs, student);
    console.log(`Filtered: ${programs.length} → ${filtered.length}`);
    if (!filtered.length) return [];

    const weights = this.getWeights(student);
    console.log('Weights:', weights);

    const scored = this.scoreAndClassify(filtered, student, weights);
    console.log(`Scored range: ${scored[scored.length-1]._matchScore} - ${scored[0]._matchScore}`);

    const selected = this.selectDiverse(scored, student);
    console.log(`Selected: ${selected.length} recommendations`);

    // 构建输出
    return selected.map(p => this.buildRecommendation(p, student));
  },

  buildRecommendation(program, student) {
    const admitRate = parseFloat(program.ar) || 0;
    const weaknesses = [];
    const suggestions = [];

    const gpa = student.gpa || 0;
    const recommendedGpa = parseFloat(program.g) || 0;
    if (gpa < recommendedGpa) {
      weaknesses.push(`GPA (${gpa}) below recommended (${recommendedGpa}) — 非硬性门槛，但影响竞争力`);
      suggestions.push(`Consider GRE Subject test in ${program.m}`);
    }

    const lang = student.language || {};
    const langScore = lang.score || 0;
    const langType = lang.type || 'IELTS';
    const minLang = langType === 'IELTS' ? (parseFloat(program.i) || 0) : (parseFloat(program.f) || 0);
    if (langScore < minLang) {
      weaknesses.push(`${langType} (${langScore}) below recommended (${minLang}) — 非硬性门槛`);
    }

    const gre = student.gre;
    const requireGre = program.gr || '';
    if ((requireGre === 'yes' || requireGre === 'required') && gre === null) {
      weaknesses.push('GRE recommended but not taken');
      suggestions.push('Register for GRE ASAP');
    } else if (gre && gre < 320 && (requireGre === 'yes' || requireGre === 'required' || requireGre === 'recommended')) {
      weaknesses.push(`GRE (${gre}) below recommended (320)`);
      suggestions.push('Consider GRE retake for a 320+ score');
    }

    if (admitRate < 10) weaknesses.push(`Very competitive (admit rate ${admitRate}%)`);
    if (program._matchScore < 6.0) suggestions.push(`Build open source projects in ${program.m}`);
    if (!weaknesses.length) {
      weaknesses.push('No significant weaknesses identified');
      suggestions.push('Apply early to maximize scholarship chances');
    }

    // 先修课匹配
    const prereqStr = program.pr || '';
    const completed = student.completed_prerequisites || [];
    const { matched, details: matchedDetails, missing: missingCourses } =
      this.matchPrerequisites(prereqStr.split(';').map(c => c.trim()).filter(Boolean), completed);
    const totalRequired = prereqStr.split(';').filter(Boolean).length;
    const ratio = totalRequired > 0 ? matched / totalRequired : 1;
    let prereqStatus = 'satisfied';
    let prereqNote = '先修课完全满足要求，可以直接申请';
    if (ratio < 1 && ratio >= 0.7) {
      prereqStatus = 'conditional';
      prereqNote = '缺失部分先修课，可以申请但需在入学前补修';
    } else if (ratio < 0.7) {
      prereqStatus = 'insufficient';
      prereqNote = '先修课缺口较大，强烈建议补修后再申请';
    }
    const prereqMatchStr = prereqStr ? `${prereqStatus !== 'insufficient' ? '满足' : '不足'} (${matched}/${totalRequired})` : '无需先修课';

    return {
      university: program.u,
      major: program.m,
      country: program.c,
      matchScore: program._matchScore,
      feasibilityLevel: program._feasibilityLevel,
      costBreakdown: {
        tuitionPerYear: program._tuition,
        livingPerYear: program._living,
        total2years: program._totalCost,
      },
      requirements: {
        recommendedGpa: recommendedGpa,
        minIelts: parseFloat(program.i) || 0,
        minToefl: parseInt(program.f) || 0,
        greRequired: requireGre || '—',
      },
      admitRate: admitRate,
      safetyScore: program._safety || 7.5,
      visaSupport: `Post-study work ${parseInt(program.vw) || 12} months`,
      weaknesses,
      improvementSuggestions: suggestions,
      prerequisiteStatus: prereqStatus,
      prerequisiteNote: prereqNote,
      prerequisiteMatch: prereqMatchStr,
      prerequisiteMissing: missingCourses,
      programUrl: program.pu || '',
    };
  },
};
