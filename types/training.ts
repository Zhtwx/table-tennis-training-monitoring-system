/** 字典节点（级联选择器 / 下拉数据源） */
export interface DictionaryNode {
  id: number;
  categoryType: 'footwork' | 'technique_tactic' | 'landing_point';
  parentId: number;
  dictCode: string;
  dictName: string;
  sortOrder: number;
  isEnabled: boolean;
  children?: DictionaryNode[];
}

export interface AthleteOption {
  id: number;
  studentNo: string;
  name: string;
}

export type ServeFrequency = '高' | '中' | '低';

/** 步法训练 · 表单提交 Payload */
export interface FootworkTrainingPayload {
  athleteId: number;
  trainingDate: string;
  footworkDictId: number;
  durationMinutes: number;
  setCount: number;
  note?: string;
}

export interface FootworkTrainingRecord extends FootworkTrainingPayload {
  id: number;
  athleteName: string;
  footworkTypeName: string;
  createdBy?: string;
  createTime: string;
}

export interface FootworkTrainingImportRow {
  studentNo: string;
  trainingDate: string;
  footworkTypeName: string;
  durationMinutes: number;
  setCount: number;
  note?: string;
}

/** 执行记录区块 */
export interface TechniqueExecutionSection {
  athleteId: number;
  trainingDate: string;
  techniqueDictId: number;
  multiBallCount: number;
  serveFrequency: ServeFrequency;
  planExecutionRate: number;
}

/** 效果反馈区块 */
export interface LandingDistributionItem {
  landingDictId: number;
  concentration: '集中' | '较为集中' | '一般' | '较为分散' | '分散';
}

export interface TechniqueFeedbackSection {
  onTableRate?: number;
  landingDistributionItems?: LandingDistributionItem[];
  qualitativeComment?: string;
}

/** 技战术训练 · 完整提交 Payload */
export interface TechniqueTacticTrainingPayload {
  execution: TechniqueExecutionSection;
  feedback: TechniqueFeedbackSection;
}

export interface TechniqueTacticTrainingRecord {
  id: number;
  athleteId: number;
  athleteName: string;
  trainingDate: string;
  techniqueDictId: number;
  techniqueCategoryName: string;
  techniqueName: string;
  multiBallCount: number;
  serveFrequency: ServeFrequency;
  planExecutionRate: number;
  onTableRate?: number;
  landingDistribution: string;
  qualitativeComment?: string;
  createTime: string;
}

export interface TechniqueTacticStats {
  totalRecords: number;
  totalBallCount: number;
  avgOnTableRate: number;
  avgPlanExecutionRate: number;
}

export interface TechniqueTacticQueryParams {
  athleteId?: number;
  techniqueDictId?: number;
  dateFrom?: string;
  dateTo?: string;
  serveFrequency?: ServeFrequency;
  page?: number;
  pageSize?: number;
}
