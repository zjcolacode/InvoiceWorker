<template>
  <div class="reimbursement-page">
    <!-- 顶部步骤导航 -->
    <el-card shadow="never" class="steps-card">
      <el-steps :active="currentStep" finish-status="process" align-center>
        <el-step
          v-for="(step, idx) in stepList"
          :key="idx"
          :title="step.title"
          :description="step.desc"
          style="cursor: pointer"
          @click.native="activeStep = idx"
        />
      </el-steps>
    </el-card>

    <!-- 步骤1：上传全量发票基础信息表 -->
    <template v-if="activeStep === 0">
      <el-card shadow="never" style="margin-top: 16px">
        <div class="toolbar-actions">
          <el-button type="primary" @click="handleUpload">
            <el-icon><Upload /></el-icon> 上传全量发票基础信息表
          </el-button>
        </div>
        <div class="toolbar-filters">
          <el-input v-model="filters.keyword" placeholder="搜索销方/购方名称" clearable style="width: 220px" @clear="handleSearch" @keyup.enter="handleSearch" />
          <el-select v-model="filters.invoice_source" placeholder="发票来源" clearable style="width: 180px" @change="handleSearch">
            <el-option v-for="opt in invoiceSourceOptions" :key="opt" :label="opt" :value="opt" />
          </el-select>
          <el-select v-model="filters.invoice_type" placeholder="发票票种" clearable style="width: 180px" @change="handleSearch">
            <el-option v-for="opt in invoiceTypeOptions" :key="opt" :label="opt" :value="opt" />
          </el-select>
          <el-select v-model="filters.verify_status" placeholder="核销状态" clearable style="width: 130px" @change="handleSearch">
            <el-option label="待核销" value="待核销" />
            <el-option label="已核销" value="已核销" />
            <el-option label="未匹配" value="未匹配" />
          </el-select>
          <el-date-picker v-model="dateRange" type="daterange" range-separator="至" start-placeholder="开始日期" end-placeholder="结束日期" value-format="YYYY-MM-DD" style="width: 260px" @change="handleDateChange" />
          <el-button type="primary" @click="handleSearch"><el-icon><Search /></el-icon> 搜索</el-button>
        </div>
      </el-card>

      <el-card shadow="never" style="margin-top: 16px">
        <el-table v-loading="loading" :data="tableData" style="width: 100%" empty-text="暂无明细数据">
          <el-table-column type="selection" width="50" />
          <el-table-column prop="digital_invoice_no" label="数电发票号码" width="180" show-overflow-tooltip>
            <template #default="{ row }">{{ row.digital_invoice_no || row.invoice_no || '-' }}</template>
          </el-table-column>
          <el-table-column prop="invoice_date" label="开票日期" width="110">
            <template #default="{ row }">{{ row.invoice_date || '-' }}</template>
          </el-table-column>
          <el-table-column prop="seller_name" label="销方名称" min-width="160" show-overflow-tooltip />
          <el-table-column prop="buyer_name" label="购买方名称" min-width="160" show-overflow-tooltip />
          <el-table-column prop="goods_or_service_name" label="货物或应税劳务名称" min-width="180" show-overflow-tooltip>
            <template #default="{ row }">{{ row.goods_or_service_name || '-' }}</template>
          </el-table-column>
          <el-table-column prop="amount" label="金额" width="110" align="right">
            <template #default="{ row }"><span v-if="row.amount">¥ {{ formatAmount(row.amount) }}</span><span v-else>-</span></template>
          </el-table-column>
          <el-table-column prop="tax_amount" label="税额" width="110" align="right">
            <template #default="{ row }"><span v-if="row.tax_amount">¥ {{ formatAmount(row.tax_amount) }}</span><span v-else>-</span></template>
          </el-table-column>
          <el-table-column prop="total_amount" label="价税合计" width="120" align="right">
            <template #default="{ row }"><span v-if="row.total_amount">¥ {{ formatAmount(row.total_amount) }}</span><span v-else>-</span></template>
          </el-table-column>
          <el-table-column prop="invoice_source" label="发票来源" width="140" show-overflow-tooltip>
            <template #default="{ row }">{{ row.invoice_source || '-' }}</template>
          </el-table-column>
          <el-table-column prop="invoice_type" label="发票票种" width="130" show-overflow-tooltip>
            <template #default="{ row }">{{ row.invoice_type || '-' }}</template>
          </el-table-column>
          <el-table-column prop="invoice_status" label="发票状态" width="100" align="center">
            <template #default="{ row }">{{ row.invoice_status || '-' }}</template>
          </el-table-column>
          <el-table-column prop="verify_status" label="核销状态" width="100" align="center">
            <template #default="{ row }">
              <el-tag :type="verifyStatusType(row.verify_status)" size="small">{{ verifyStatusText(row.verify_status) }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="match_method" label="核销方式" width="110" align="center">
            <template #default="{ row }">
              <span v-if="row.match_method">{{ row.match_method }}</span>
              <span v-else style="color: #999">-</span>
            </template>
          </el-table-column>
          <el-table-column label="操作" width="90" fixed="right" align="center">
            <template #default="{ row }">
              <el-button link type="primary" size="small" @click="showDetail(row as InvoiceDetailItem)">详情</el-button>
            </template>
          </el-table-column>
        </el-table>
        <div class="pagination-wrap">
          <el-pagination v-model:current-page="pagination.page" v-model:page-size="pagination.pageSize" :total="pagination.total" :page-sizes="[10, 20, 50, 100]" layout="total, sizes, prev, pager, next" @size-change="loadData" @current-change="loadData" />
        </div>
      </el-card>
    </template>

    <!-- 步骤2：邮箱匹配 -->
    <template v-if="activeStep === 1">
      <!-- 邮箱配置区 -->
      <el-card shadow="never" style="margin-top: 16px">
        <template #header>
          <div class="card-header">
            <span class="card-header__title">邮箱配置</span>
            <div>
              <el-button :icon="Refresh" @click="loadEmailConfigs" :loading="emailConfigLoading">刷新</el-button>
              <el-button type="primary" :icon="Plus" @click="openCreateEmail">添加邮箱</el-button>
            </div>
          </div>
        </template>
        <el-table v-loading="emailConfigLoading" :data="emailConfigs" stripe empty-text="暂无邮箱配置">
          <el-table-column prop="email_address" label="邮箱地址" min-width="200" show-overflow-tooltip />
          <el-table-column label="服务器 / 端口" min-width="200">
            <template #default="{ row }">{{ row.imap_server }}:{{ row.port }}
              <el-tag v-if="row.use_ssl" type="primary" size="small" effect="plain" style="margin-left:6px">SSL</el-tag>
            </template>
          </el-table-column>
          <el-table-column label="状态" width="100" align="center">
            <template #default="{ row }">
              <el-tag :type="row.is_active ? 'success' : 'info'" size="small">{{ row.is_active ? '启用' : '停用' }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column label="最后拉取" width="170">
            <template #default="{ row }">{{ row.last_check_at ? formatTime(row.last_check_at) : '尚未拉取' }}</template>
          </el-table-column>
          <el-table-column label="操作" width="240" align="right">
            <template #default="{ row }">
              <el-button link type="primary" size="small" :loading="testingId === row.id" @click="handleTestConnection(row as ReimbEmailConfig)">测试</el-button>
              <el-button link type="primary" size="small" @click="openEditEmail(row as ReimbEmailConfig)">编辑</el-button>
              <el-button link type="danger" size="small" @click="handleDeleteEmail(row as ReimbEmailConfig)">删除</el-button>
            </template>
          </el-table-column>
        </el-table>
      </el-card>

      <!-- 拉取操作区 -->
      <el-card shadow="never" style="margin-top: 16px">
        <template #header><span class="card-header__title">拉取操作</span></template>
        <el-descriptions :column="2" border size="small" style="margin-bottom: 16px">
          <el-descriptions-item label="发票数据日期范围">{{ invoiceDateRange }}</el-descriptions-item>
        </el-descriptions>
        <div style="display:flex; gap:12px; align-items:center; margin-bottom:16px;">
          <el-date-picker v-model="fetchDateRange" type="daterange" range-separator="至" start-placeholder="开始" end-placeholder="结束" value-format="YYYY-MM-DD" style="width:300px" />
          <el-button type="primary" :loading="fetching" @click="handleFetchEmails"><el-icon><Message /></el-icon> 拉取邮件</el-button>
          <el-button type="success" :loading="verifying" @click="handleVerify"><el-icon><Check /></el-icon> 执行匹配核销</el-button>
        </div>
        <el-table v-loading="emailMessagesLoading" :data="emailMessages" stripe empty-text="暂无拉取邮件">
          <el-table-column prop="subject" label="主题" min-width="200" show-overflow-tooltip>
            <template #default="{ row }">{{ row.subject || '(无主题)' }}</template>
          </el-table-column>
          <el-table-column prop="sender" label="发件人" width="180" show-overflow-tooltip />
          <el-table-column prop="attachment_name" label="附件名" min-width="200" show-overflow-tooltip>
            <template #default="{ row }">{{ row.attachment_name || '-' }}</template>
          </el-table-column>
          <el-table-column prop="received_at" label="收件时间" width="170">
            <template #default="{ row }">{{ row.received_at ? formatTime(row.received_at) : '-' }}</template>
          </el-table-column>
        </el-table>
        <div class="pagination-wrap">
          <el-pagination v-model:current-page="emailMsgPagination.page" v-model:page-size="emailMsgPagination.pageSize" :total="emailMsgPagination.total" :page-sizes="[10, 20, 50]" layout="total, prev, pager, next" @size-change="loadEmailMessages" @current-change="loadEmailMessages" />
        </div>
      </el-card>


    </template>

    <!-- 步骤3：手动匹配 -->
    <template v-if="activeStep === 2">
      <el-card shadow="never" style="margin-top: 16px">
        <el-alert type="info" :closable="false" show-icon title="多模态大模型视觉识别匹配 - 上传发票文件进行AI识别匹配" style="margin-bottom: 16px" />
        <el-table :data="unmatchedInvoices" v-loading="unmatchedLoading" stripe empty-text="暂无未匹配发票">
          <el-table-column prop="digital_invoice_no" label="发票号码" width="200" show-overflow-tooltip>
            <template #default="{ row }">{{ row.digital_invoice_no || row.invoice_no || '-' }}</template>
          </el-table-column>
          <el-table-column prop="invoice_date" label="开票日期" width="120">
            <template #default="{ row }">{{ (row.invoice_date || '').substring(0, 10) }}</template>
          </el-table-column>
          <el-table-column prop="seller_name" label="销方名称" min-width="160" show-overflow-tooltip />
          <el-table-column prop="total_amount" label="价税合计" width="120" align="right">
            <template #default="{ row }"><span v-if="row.total_amount">¥ {{ formatAmount(row.total_amount) }}</span><span v-else>-</span></template>
          </el-table-column>
          <el-table-column prop="verify_status" label="状态" width="100" align="center">
            <template #default="{ row }"><el-tag type="danger" size="small">{{ row.verify_status }}</el-tag></template>
          </el-table-column>
          <el-table-column label="操作" width="120" align="center" fixed="right">
            <template #default="{ row }">
              <el-button type="primary" size="small" @click="openManualMatch(row as InvoiceDetailItem)">手工匹配</el-button>
            </template>
          </el-table-column>
        </el-table>
      </el-card>
    </template>

    <!-- 步骤4：报销单管理 -->
    <template v-if="activeStep === 3">
      <el-card shadow="never" style="margin-top: 16px">
        <el-alert type="success" :closable="false" show-icon title="已核销发票基础信息表 - 展示所有已完成匹配核销的发票数据" style="margin-bottom: 16px" />
        <el-form :inline="true" :model="matchedFilter" class="matched-filter-form" style="margin-bottom: 16px">
          <el-form-item label="开票日期">
            <el-date-picker v-model="matchedFilter.dateRange" type="daterange" range-separator="至" start-placeholder="开始日期" end-placeholder="结束日期" value-format="YYYY-MM-DD" style="width: 260px" />
          </el-form-item>
          <el-form-item label="销方名称">
            <el-input v-model="matchedFilter.sellerName" placeholder="输入销方名称" clearable style="width: 200px" />
          </el-form-item>
          <el-form-item label="报销状态">
            <el-select v-model="matchedFilter.reimburseStatus" placeholder="全部状态" clearable style="width: 150px">
              <el-option label="全部" value="" />
              <el-option label="待报销" value="待报销" />
              <el-option label="已报销" value="已报销" />
            </el-select>
          </el-form-item>
          <el-form-item label="发票票种">
            <el-select v-model="matchedFilter.invoiceType" placeholder="全部票种" clearable style="width: 180px">
              <el-option v-for="opt in matchedInvoiceTypeOptions" :key="opt" :label="opt" :value="opt" />
            </el-select>
          </el-form-item>
          <el-form-item label="核销方式">
            <el-select v-model="matchedFilter.matchMethod" placeholder="全部方式" clearable style="width: 150px">
              <el-option v-for="opt in matchedMethodOptions" :key="opt" :label="opt" :value="opt" />
            </el-select>
          </el-form-item>
          <el-form-item>
            <el-button type="primary" @click="handleMatchedFilterSearch"><el-icon><Search /></el-icon> 查询</el-button>
            <el-button @click="handleMatchedFilterReset"><el-icon><Refresh /></el-icon> 重置</el-button>
          </el-form-item>
        </el-form>
        <div style="display: flex; justify-content: flex-end; margin-bottom: 12px;">
          <el-button type="primary" @click="handleSubmitReimburse" :loading="submittingReimburse">
            报销提交
          </el-button>
        </div>
        <el-table ref="matchedTableRef" v-loading="matchedLoading" :data="filteredMatchedInvoices" stripe empty-text="暂无已核销发票数据" style="width: 100%">
          <el-table-column type="selection" width="50" />
          <el-table-column prop="digital_invoice_no" label="数电发票号码" width="200" show-overflow-tooltip>
            <template #default="{ row }">{{ row.digital_invoice_no || row.invoice_no || '-' }}</template>
          </el-table-column>
          <el-table-column prop="invoice_date" label="开票日期" width="120">
            <template #default="{ row }">{{ (row.invoice_date || '').substring(0, 10) || '-' }}</template>
          </el-table-column>
          <el-table-column prop="seller_name" label="销方名称" min-width="160" show-overflow-tooltip />
          <el-table-column prop="buyer_name" label="购买方名称" min-width="160" show-overflow-tooltip />
          <el-table-column prop="amount" label="金额" width="110" align="right">
            <template #default="{ row }"><span v-if="row.amount">¥ {{ formatAmount(row.amount) }}</span><span v-else>-</span></template>
          </el-table-column>
          <el-table-column prop="tax_amount" label="税额" width="110" align="right">
            <template #default="{ row }"><span v-if="row.tax_amount">¥ {{ formatAmount(row.tax_amount) }}</span><span v-else>-</span></template>
          </el-table-column>
          <el-table-column prop="total_amount" label="价税合计" width="120" align="right">
            <template #default="{ row }"><span v-if="row.total_amount">¥ {{ formatAmount(row.total_amount) }}</span><span v-else>-</span></template>
          </el-table-column>
          <el-table-column prop="invoice_source" label="发票来源" width="140" show-overflow-tooltip>
            <template #default="{ row }">{{ row.invoice_source || '-' }}</template>
          </el-table-column>
          <el-table-column prop="invoice_type" label="发票票种" width="130" show-overflow-tooltip>
            <template #default="{ row }">{{ row.invoice_type || '-' }}</template>
          </el-table-column>
          <el-table-column prop="match_method" label="核销方式" width="110" align="center">
            <template #default="{ row }">
              <el-tag v-if="row.match_method" :type="row.match_method === '邮箱匹配' ? 'primary' : 'success'" size="small">{{ row.match_method }}</el-tag>
              <span v-else style="color:#999">-</span>
            </template>
          </el-table-column>
          <el-table-column prop="verified_at" label="核销时间" width="170">
            <template #default="{ row }">{{ row.verified_at ? formatTime(row.verified_at) : '-' }}</template>
          </el-table-column>
          <el-table-column prop="reimburse_status" label="报销状态" width="110" align="center">
            <template #default="{ row }">
              <el-tag v-if="row.reimburse_status === '已报销'" type="success" size="small">已报销</el-tag>
              <el-tag v-else type="info" size="small">待报销</el-tag>
            </template>
          </el-table-column>
        </el-table>
        <div class="pagination-wrap">
          <el-pagination v-model:current-page="matchedPagination.page" v-model:page-size="matchedPagination.pageSize" :total="matchedPaginationTotal" :page-sizes="[10, 20, 50, 100]" layout="total, sizes, prev, pager, next" @size-change="loadMatchedInvoices" @current-change="loadMatchedInvoices" />
        </div>
      </el-card>
    </template>

    <!-- 底部通用记录区域 -->
    <el-card v-if="activeStep === 0" shadow="never" style="margin-top: 24px">
      <template #header>
        <div style="display:flex; align-items:center; gap:8px; cursor:pointer;" @click="uploadLogsCollapsed = !uploadLogsCollapsed">
          <el-icon :style="{ transform: uploadLogsCollapsed ? 'rotate(-90deg)' : 'rotate(0deg)', transition: 'transform 0.2s' }"><ArrowDown /></el-icon>
          <span style="font-weight: bold;">上传记录</span>
        </div>
      </template>
      <div v-show="!uploadLogsCollapsed">
        <el-table :data="uploadLogs" v-loading="uploadLogsLoading" stripe>
          <el-table-column prop="created_at" label="上传时间" width="180" :formatter="(_r: any, _c: any, val: string) => formatTime(val)" />
          <el-table-column prop="original_filename" label="文件名" min-width="200" show-overflow-tooltip />
          <el-table-column prop="uploader_username" label="上传人" width="120" />
          <el-table-column prop="total_count" label="导入条数" width="100" align="center" />
        </el-table>
        <div class="pagination-wrap">
          <el-pagination v-model:current-page="uploadLogsPagination.page" v-model:page-size="uploadLogsPagination.pageSize" :total="uploadLogsPagination.total" :page-sizes="[10, 20, 50]" layout="total, sizes, prev, pager, next" @size-change="loadUploadLogs" @current-change="loadUploadLogs" />
        </div>
      </div>
    </el-card>

    <el-card v-if="activeStep === 1" shadow="never" style="margin-top: 16px">
      <template #header>
        <div style="display:flex; align-items:center; gap:8px; cursor:pointer;" @click="fetchLogsCollapsed = !fetchLogsCollapsed">
          <el-icon :style="{ transform: fetchLogsCollapsed ? 'rotate(-90deg)' : 'rotate(0deg)', transition: 'transform 0.2s' }"><ArrowDown /></el-icon>
          <span style="font-weight: bold;">拉取记录</span>
        </div>
      </template>
      <div v-show="!fetchLogsCollapsed">
        <el-table :data="fetchLogs" v-loading="fetchLogsLoading" stripe>
          <el-table-column prop="fetch_time" label="时间" width="180">
            <template #default="{ row }">{{ row.fetch_time ? formatTime(row.fetch_time) : '-' }}</template>
          </el-table-column>
          <el-table-column prop="email_address" label="邮箱" min-width="200" show-overflow-tooltip />
          <el-table-column prop="total_emails_checked" label="检索数" width="100" align="center" />
          <el-table-column prop="new_emails_count" label="新增数" width="100" align="center">
            <template #default="{ row }"><span :style="{ color: row.new_emails_count > 0 ? '#67C23A' : '' }">{{ row.new_emails_count }}</span></template>
          </el-table-column>
          <el-table-column prop="status" label="状态" width="100" align="center">
            <template #default="{ row }">
              <el-tag :type="row.status === 'success' ? 'success' : row.status === 'failed' ? 'danger' : 'info'" size="small">{{ row.status }}</el-tag>
            </template>
          </el-table-column>
        </el-table>
        <div class="pagination-wrap">
          <el-pagination v-model:current-page="fetchLogsPagination.page" v-model:page-size="fetchLogsPagination.pageSize" :total="fetchLogsPagination.total" :page-sizes="[10, 20, 50]" layout="total, sizes, prev, pager, next" @size-change="loadFetchLogs" @current-change="loadFetchLogs" />
        </div>
      </div>
    </el-card>

    <el-card v-if="activeStep === 2" shadow="never" style="margin-top: 16px">
      <template #header>
        <div style="display:flex; align-items:center; gap:8px; cursor:pointer;" @click="manualMatchRecordsCollapsed = !manualMatchRecordsCollapsed">
          <el-icon :style="{ transform: manualMatchRecordsCollapsed ? 'rotate(-90deg)' : 'rotate(0deg)', transition: 'transform 0.2s' }"><ArrowDown /></el-icon>
          <span style="font-weight: bold;">手工匹配记录</span>
        </div>
      </template>
      <div v-show="!manualMatchRecordsCollapsed">
        <el-table :data="manualMatchRecords" v-loading="manualMatchRecordsLoading" stripe>
          <el-table-column prop="created_at" label="时间" width="180">
            <template #default="{ row }">{{ row.created_at ? formatTime(row.created_at) : '-' }}</template>
          </el-table-column>
          <el-table-column prop="original_filename" label="上传文件" min-width="200" show-overflow-tooltip />
          <el-table-column prop="recognized_invoice_no" label="识别号码" width="200" show-overflow-tooltip>
            <template #default="{ row }">{{ row.recognized_invoice_no || '-' }}</template>
          </el-table-column>
          <el-table-column prop="match_status" label="匹配状态" width="100" align="center">
            <template #default="{ row }">
              <el-tag :type="row.match_status === '成功' ? 'success' : 'danger'" size="small">{{ row.match_status }}</el-tag>
            </template>
          </el-table-column>
        </el-table>
        <div class="pagination-wrap">
          <el-pagination v-model:current-page="manualMatchRecordsPagination.page" v-model:page-size="manualMatchRecordsPagination.pageSize" :total="manualMatchRecordsPagination.total" :page-sizes="[10, 20, 50]" layout="total, sizes, prev, pager, next" @size-change="loadManualMatchRecords" @current-change="loadManualMatchRecords" />
        </div>
      </div>
    </el-card>

    <el-card v-if="activeStep === 1" shadow="never" style="margin-top: 16px">
      <template #header>
        <div style="display:flex; align-items:center; gap:8px; cursor:pointer;" @click="verifyRecordsCollapsed = !verifyRecordsCollapsed">
          <el-icon :style="{ transform: verifyRecordsCollapsed ? 'rotate(-90deg)' : 'rotate(0deg)', transition: 'transform 0.2s' }"><ArrowDown /></el-icon>
          <span style="font-weight: bold;">核销记录</span>
        </div>
      </template>
      <div v-show="!verifyRecordsCollapsed">
        <el-table :data="verifyRecords" v-loading="verifyRecordsLoading" stripe>
          <el-table-column prop="created_at" label="核销时间" width="180">
            <template #default="{ row }">{{ formatTime(row.created_at) }}</template>
          </el-table-column>
          <el-table-column prop="original_filename" label="文件名" min-width="200" show-overflow-tooltip />
          <el-table-column prop="uploader_username" label="操作人" width="120" />
          <el-table-column prop="total_count" label="总数" width="80" align="center" />
          <el-table-column prop="matched_count" label="已核销" width="80" align="center">
            <template #default="{ row }"><span style="color:#67C23A;font-weight:bold">{{ row.matched_count }}</span></template>
          </el-table-column>
          <el-table-column prop="unmatched_count" label="未匹配" width="80" align="center">
            <template #default="{ row }">
              <span v-if="row.unmatched_count > 0" style="color:#F56C6C;font-weight:bold">{{ row.unmatched_count }}</span>
              <span v-else>0</span>
            </template>
          </el-table-column>
          <el-table-column label="操作" width="120" align="center">
            <template #default="{ row }">
              <el-button v-if="row.unmatched_count > 0" type="primary" link size="small" @click="showUnmatched(row)">查看详情</el-button>
            </template>
          </el-table-column>
        </el-table>
        <div class="pagination-wrap">
          <el-pagination v-model:current-page="verifyRecordsPagination.page" v-model:page-size="verifyRecordsPagination.pageSize" :total="verifyRecordsPagination.total" :page-sizes="[10, 20, 50]" layout="total, sizes, prev, pager, next" @size-change="loadVerifyRecords" @current-change="loadVerifyRecords" />
        </div>
      </div>
    </el-card>

    <el-card v-if="activeStep === 3" shadow="never" style="margin-top: 16px">
      <template #header>
        <div style="display:flex; align-items:center; gap:8px; cursor:pointer;" @click="reimbRecordsCollapsed = !reimbRecordsCollapsed">
          <el-icon :style="{ transform: reimbRecordsCollapsed ? 'rotate(-90deg)' : 'rotate(0deg)', transition: 'transform 0.2s' }"><ArrowDown /></el-icon>
          <span style="font-weight: bold;">报销申请记录</span>
        </div>
      </template>
      <div v-show="!reimbRecordsCollapsed">
        <el-table :data="reimbApplications" v-loading="reimbApplicationsLoading" stripe empty-text="暂无报销申请记录">
          <el-table-column prop="reimburse_no" label="报销单号" width="200" show-overflow-tooltip />
          <el-table-column prop="applicant_name" label="申请人" width="100" />
          <el-table-column prop="department" label="部门" width="100" />
          <el-table-column prop="category" label="报销类别" min-width="160" show-overflow-tooltip />
          <el-table-column prop="total_amount" label="金额" width="120" align="right">
            <template #default="{ row }"><span v-if="row.total_amount">¥ {{ formatAmount(row.total_amount) }}</span><span v-else>-</span></template>
          </el-table-column>
          <el-table-column prop="status" label="状态" width="100" align="center">
            <template #default="{ row }">
              <el-tag :type="row.status === '已通过' ? 'success' : row.status === '已拒绝' ? 'danger' : 'primary'" size="small">{{ row.status }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="created_at" label="提交时间" width="180">
            <template #default="{ row }">{{ row.created_at ? formatTime(row.created_at) : '-' }}</template>
          </el-table-column>
          <el-table-column label="操作" width="100" fixed="right" align="center">
            <template #default="{ row }">
              <el-button type="primary" link size="small" :loading="row._exporting" @click="handleExportPDF(row)">
                导出
              </el-button>
            </template>
          </el-table-column>
        </el-table>
        <div class="pagination-wrap">
          <el-pagination v-model:current-page="reimbApplicationsPagination.page" v-model:page-size="reimbApplicationsPagination.pageSize" :total="reimbApplicationsPagination.total" :page-sizes="[10, 20, 50]" layout="total, sizes, prev, pager, next" @size-change="loadReimbApplications" @current-change="loadReimbApplications" />
        </div>
      </div>
    </el-card>

    <!-- 未匹配详情弹窗 -->
    <el-dialog v-model="unmatchedDialogVisible" title="未匹配的发票号码" width="500px">
      <div v-if="currentUnmatchedList.length > 0" style="display:flex;flex-wrap:wrap;gap:8px">
        <el-tag v-for="no in currentUnmatchedList" :key="no" type="danger">{{ no }}</el-tag>
      </div>
      <el-empty v-else description="暂无未匹配的发票号码" :image-size="80" />
      <template #footer><el-button @click="unmatchedDialogVisible = false">关闭</el-button></template>
    </el-dialog>

    <!-- 上传对话框 -->
    <el-dialog v-model="uploadDialogVisible" title="上传全量发票基础信息表" width="600px" :close-on-click-modal="false" @close="resetUploadDialog">
      <el-upload ref="uploadRef" drag :auto-upload="false" :limit="1" accept=".xlsx" :on-change="handleFileChange" :on-remove="handleFileRemove" :on-exceed="handleExceed" :file-list="uploadFileList" :disabled="uploading" class="detail-upload">
        <el-icon class="el-icon--upload"><UploadFilled /></el-icon>
        <div class="el-upload__text">将文件拖到此处，或<em>点击上传</em></div>
        <template #tip><div class="el-upload__tip">仅支持 .xlsx 格式，文件需包含「发票基础信息」工作表且表头符合 19 列标准模板</div></template>
      </el-upload>
      <template #footer>
        <el-button @click="uploadDialogVisible = false" :disabled="uploading">取消</el-button>
        <el-button type="primary" :loading="uploading" :disabled="!selectedFile" @click="handleUploadSubmit">确认上传</el-button>
      </template>
    </el-dialog>

    <!-- 核销结果对话框 -->
    <el-dialog v-model="verifyResultVisible" title="核销结果" width="640px">
      <el-descriptions v-if="verifyResult" :column="3" border>
        <el-descriptions-item label="待核销总数"><span class="result-number">{{ verifyResult.total_count }}</span></el-descriptions-item>
        <el-descriptions-item label="已核销"><span class="result-number result-success">{{ verifyResult.matched_count }}</span></el-descriptions-item>
        <el-descriptions-item label="未匹配"><span class="result-number" :class="{ 'result-danger': verifyResult.unmatched_count > 0 }">{{ verifyResult.unmatched_count }}</span></el-descriptions-item>
      </el-descriptions>
      <div v-if="verifyResult && verifyResult.unmatched_count > 0" class="unmatched-area">
        <div class="unmatched-title">未匹配的发票号码：</div>
        <div class="unmatched-list">
          <el-tag v-for="(no, idx) in verifyResult.unmatched_details" :key="idx" type="danger" size="small">{{ no }}</el-tag>
        </div>
      </div>
      <template #footer><el-button type="primary" @click="verifyResultVisible = false">关闭</el-button></template>
    </el-dialog>

    <!-- 明细详情弹窗 -->
    <el-dialog v-model="detailVisible" title="发票明细详情" width="900px">
      <el-descriptions v-if="currentDetail" :column="2" border size="small">
        <el-descriptions-item label="序号">{{ currentDetail.serial_no || '-' }}</el-descriptions-item>
        <el-descriptions-item label="发票代码">{{ currentDetail.invoice_code || '-' }}</el-descriptions-item>
        <el-descriptions-item label="发票号码">{{ currentDetail.invoice_no || '-' }}</el-descriptions-item>
        <el-descriptions-item label="数电发票号码">{{ currentDetail.digital_invoice_no || '-' }}</el-descriptions-item>
        <el-descriptions-item label="开票日期">{{ currentDetail.invoice_date || '-' }}</el-descriptions-item>
        <el-descriptions-item label="开票人">{{ currentDetail.issuer || '-' }}</el-descriptions-item>
        <el-descriptions-item label="销方识别号">{{ currentDetail.seller_tax_no || '-' }}</el-descriptions-item>
        <el-descriptions-item label="销方名称">{{ currentDetail.seller_name || '-' }}</el-descriptions-item>
        <el-descriptions-item label="购方识别号">{{ currentDetail.buyer_tax_no || '-' }}</el-descriptions-item>
        <el-descriptions-item label="购买方名称">{{ currentDetail.buyer_name || '-' }}</el-descriptions-item>
        <el-descriptions-item label="金额">{{ currentDetail.amount || '-' }}</el-descriptions-item>
        <el-descriptions-item label="税额">{{ currentDetail.tax_amount || '-' }}</el-descriptions-item>
        <el-descriptions-item label="价税合计">{{ currentDetail.total_amount || '-' }}</el-descriptions-item>
        <el-descriptions-item label="发票来源">{{ currentDetail.invoice_source || '-' }}</el-descriptions-item>
        <el-descriptions-item label="发票票种">{{ currentDetail.invoice_type || '-' }}</el-descriptions-item>
        <el-descriptions-item label="发票状态">{{ currentDetail.invoice_status || '-' }}</el-descriptions-item>
        <el-descriptions-item label="是否正数发票">{{ currentDetail.is_positive || '-' }}</el-descriptions-item>
        <el-descriptions-item label="风险等级">{{ currentDetail.risk_level || '-' }}</el-descriptions-item>
        <el-descriptions-item label="备注" :span="2">{{ currentDetail.remark || '-' }}</el-descriptions-item>
        <el-descriptions-item label="核销状态">
          <el-tag :type="verifyStatusType(currentDetail.verify_status)" size="small">{{ verifyStatusText(currentDetail.verify_status) }}</el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="核销时间">{{ currentDetail.verified_at || '-' }}</el-descriptions-item>
      </el-descriptions>
    </el-dialog>

    <!-- 邮箱添加/编辑对话框 -->
    <el-dialog v-model="emailDialogVisible" :title="emailEditing ? '编辑邮箱' : '添加邮箱'" width="540px" :close-on-click-modal="false" destroy-on-close>
      <el-form ref="emailFormRef" :model="emailForm" :rules="emailRules" label-position="top">
        <el-form-item label="邮箱地址" prop="email_address">
          <el-input v-model="emailForm.email_address" placeholder="finance@company.com" />
        </el-form-item>
        <el-form-item label="IMAP 服务器" prop="imap_server">
          <el-input v-model="emailForm.imap_server" placeholder="imap.qq.com" />
        </el-form-item>
        <el-row :gutter="16">
          <el-col :span="10">
            <el-form-item label="端口" prop="port">
              <el-input-number v-model="emailForm.port" :min="1" :max="65535" :controls="false" style="width:100%" />
            </el-form-item>
          </el-col>
          <el-col :span="6">
            <el-form-item label="SSL">
              <el-switch v-model="emailForm.use_ssl" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-form-item label="密码 / 授权码" prop="password">
          <el-input v-model="emailForm.password" type="password" show-password :placeholder="emailEditing ? '留空则不修改' : '授权码'" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="emailDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="emailSaving" @click="handleEmailSubmit">{{ emailEditing ? '保存' : '添加' }}</el-button>
      </template>
    </el-dialog>

    <!-- 手工匹配对话框 -->
    <el-dialog v-model="manualMatchDialogVisible" title="手工匹配 - AI视觉识别" width="700px" :close-on-click-modal="false" destroy-on-close>
      <div v-if="manualMatchTarget">
        <el-descriptions :column="2" border size="small" style="margin-bottom: 20px">
          <el-descriptions-item label="发票号码">{{ manualMatchTarget.digital_invoice_no || manualMatchTarget.invoice_no || '-' }}</el-descriptions-item>
          <el-descriptions-item label="销方名称">{{ manualMatchTarget.seller_name || '-' }}</el-descriptions-item>
          <el-descriptions-item label="开票日期">{{ (manualMatchTarget.invoice_date || '').substring(0, 10) }}</el-descriptions-item>
          <el-descriptions-item label="价税合计">{{ manualMatchTarget.total_amount ? '¥ ' + formatAmount(manualMatchTarget.total_amount) : '-' }}</el-descriptions-item>
        </el-descriptions>
        <el-upload ref="manualMatchUploadRef" drag :auto-upload="false" :limit="1" accept=".pdf,.jpg,.jpeg,.png" :on-change="handleManualMatchFileChange" :on-remove="handleManualMatchFileRemove" :on-exceed="() => ElMessage.warning('仅支持上传一个文件')" :file-list="manualMatchFileList" :disabled="manualMatching" class="detail-upload">
          <el-icon class="el-icon--upload"><UploadFilled /></el-icon>
          <div class="el-upload__text">将发票PDF或图片拖到此处，或<em>点击上传</em></div>
          <template #tip><div class="el-upload__tip">支持 PDF、JPG、PNG 格式</div></template>
        </el-upload>
        <!-- 识别结果 -->
        <div v-if="manualMatchResultData" style="margin-top: 16px">
          <el-alert v-if="manualMatchResultData.match_result === 'matched'" type="success" :closable="false" show-icon>
            <template #title>匹配成功！识别发票号码：{{ manualMatchResultData.recognized_invoice_no }}</template>
          </el-alert>
          <el-alert v-else-if="manualMatchResultData.match_result === 'not_matched'" type="warning" :closable="false" show-icon>
            <template #title>匹配失败：{{ manualMatchResultData.message }}</template>
            <template #default><span v-if="manualMatchResultData.recognized_invoice_no">识别到的发票号码：{{ manualMatchResultData.recognized_invoice_no }}</span></template>
          </el-alert>
          <el-alert v-else type="error" :closable="false" show-icon>
            <template #title>识别失败：{{ manualMatchResultData.message }}</template>
          </el-alert>
        </div>
      </div>
      <template #footer>
        <el-button @click="manualMatchDialogVisible = false" :disabled="manualMatching">关闭</el-button>
        <el-button type="primary" :loading="manualMatching" :disabled="!manualMatchFile" @click="handleManualMatchSubmit">
          {{ manualMatching ? 'AI识别中...' : '开始识别匹配' }}
        </el-button>
      </template>
    </el-dialog>

    <!-- 报销申请对话框 -->
    <el-dialog v-model="reimburseDialogVisible" title="提交报销申请" width="800px" :close-on-click-modal="false" destroy-on-close>
      <el-form ref="reimburseFormRef" :model="reimburseFormData" :rules="reimburseRules" label-position="top">
        <!-- 报销人信息 -->
        <el-card shadow="never" style="margin-bottom: 16px">
          <template #header><span style="font-weight:600">报销人信息</span></template>
          <el-row :gutter="16">
            <el-col :span="12">
              <el-form-item label="报销人名称">
                <el-input :model-value="userStore.userInfo?.full_name || userStore.userInfo?.username || '-'" disabled />
              </el-form-item>
            </el-col>
            <el-col :span="12">
              <el-form-item label="报销人岗位">
                <el-input :model-value="userStore.userInfo?.position || '-'" disabled />
              </el-form-item>
            </el-col>
          </el-row>
        </el-card>

        <!-- 报销基本信息 -->
        <el-card shadow="never" style="margin-bottom: 16px">
          <template #header>
            <div style="display:flex;justify-content:space-between;align-items:center">
              <span style="font-weight:600">报销基本信息</span>
              <el-button type="primary" size="small" @click="addReimburseRow">+ 添加项目</el-button>
            </div>
          </template>
          <el-row :gutter="16" style="margin-bottom: 12px">
            <el-col :span="12">
              <el-form-item label="报销日期" prop="reimburse_date">
                <el-date-picker v-model="reimburseFormData.reimburse_date" type="date" value-format="YYYY-MM-DD" style="width:100%" placeholder="选择日期" />
              </el-form-item>
            </el-col>
            <el-col :span="12">
              <el-form-item label="报销部门" prop="department">
                <el-select v-model="reimburseFormData.department" placeholder="选择部门" style="width:100%">
                  <el-option v-for="d in departmentOptions" :key="d" :label="d" :value="d" />
                </el-select>
              </el-form-item>
            </el-col>
          </el-row>
          <el-table :data="reimburseItems" border size="small" style="width:100%">
            <el-table-column label="发生日期" width="160">
              <template #default="{ row }">
                <el-date-picker v-model="row.date" type="date" value-format="YYYY-MM-DD" placeholder="选择日期" size="small" style="width:100%" />
              </template>
            </el-table-column>
            <el-table-column label="报销内容" min-width="160">
              <template #default="{ row }">
                <el-input v-model="row.content" placeholder="报销内容" size="small" style="width:100%" />
              </template>
            </el-table-column>
            <el-table-column label="单据张数" width="100">
              <template #default="{ row }">
                <el-input-number v-model="row.receipt_count" :min="0" :controls="false" size="small" style="width:100%" />
              </template>
            </el-table-column>
            <el-table-column label="金额" width="140">
              <template #default="{ row }">
                <el-input-number v-model="row.amount" :min="0" :precision="2" :controls="false" size="small" style="width:100%" placeholder="0.00" />
              </template>
            </el-table-column>
            <el-table-column label="备注" min-width="120">
              <template #default="{ row }">
                <el-input v-model="row.remark" size="small" placeholder="选填" />
              </template>
            </el-table-column>
            <el-table-column label="操作" width="60" align="center">
              <template #default="{ $index }">
                <el-button link type="danger" size="small" @click="removeReimburseRow($index)">删除</el-button>
              </template>
            </el-table-column>
          </el-table>
          <!-- 合计行 -->
          <div style="display:flex;justify-content:flex-end;margin-top:12px;font-weight:600;font-size:14px;">
            合计人民币：<span style="color:#409EFF;margin-left:8px">¥ {{ reimburseItemsTotal }}</span>
          </div>
        </el-card>

        <!-- 发票信息 -->
        <el-card shadow="never" style="margin-bottom: 16px">
          <template #header>
            <div style="display:flex;justify-content:space-between;align-items:center">
              <span style="font-weight:600">发票信息</span>
              <span style="color:#409EFF;font-weight:600">合计金额：¥ {{ reimburseTotal }}</span>
            </div>
          </template>
          <el-table :data="reimburseSelectedInvoices" stripe size="small" max-height="200">
            <el-table-column prop="digital_invoice_no" label="发票号码" width="200" show-overflow-tooltip>
              <template #default="{ row }">{{ row.digital_invoice_no || row.invoice_no || '-' }}</template>
            </el-table-column>
            <el-table-column prop="invoice_date" label="开票日期" width="110">
              <template #default="{ row }">{{ (row.invoice_date || '').substring(0, 10) }}</template>
            </el-table-column>
            <el-table-column prop="seller_name" label="销方名称" min-width="160" show-overflow-tooltip />
            <el-table-column prop="total_amount" label="价税合计" width="120" align="right">
              <template #default="{ row }"><span v-if="row.total_amount">¥ {{ formatAmount(row.total_amount) }}</span><span v-else>-</span></template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-form>

      <template #footer>
        <el-button @click="reimburseDialogVisible = false" :disabled="submittingReimburse">取消</el-button>
        <el-button type="primary" :loading="submittingReimburse" @click="handleReimburseSubmit">提交</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import type { FormInstance, FormRules, UploadFile, UploadInstance, UploadUserFile } from 'element-plus'
import { ArrowDown, Check, Message, Plus, Refresh, Search, Upload, UploadFilled } from '@element-plus/icons-vue'
import {
  getInvoiceDetails,
  getReimbursementRecords,
  getUploadLogs,
  uploadInvoiceDetail,
  verifyInvoices,
  type InvoiceDetailItem,
  type VerifyResult,
  getReimbEmailConfigs,
  createReimbEmailConfig,
  updateReimbEmailConfig,
  deleteReimbEmailConfig,
  testReimbEmailConnection,
  fetchReimbEmails,
  getReimbEmailMessages,
  getReimbEmailFetchLogs,
  type ReimbEmailConfig,
  type ReimbEmailMessage,
  type ReimbEmailFetchLog,
  type ReimbEmailTestResult,
  type ReimbEmailFetchResult,
  manualMatchInvoice,
  getManualMatchRecords,
  createReimburseApplication,
  getReimburseApplications,
  exportReimburseApplicationPdf,
  type ManualMatchResult,
  type ManualMatchRecord as ManualMatchRecordType,
} from '@/api/reimbursement'
import { useUserStore } from '@/stores/user'

const userStore = useUserStore()

// ============================================================
// 底部记录卡片折叠状态
// ============================================================
const uploadLogsCollapsed = ref(false)
const fetchLogsCollapsed = ref(false)
const manualMatchRecordsCollapsed = ref(false)
const verifyRecordsCollapsed = ref(false)
const reimbRecordsCollapsed = ref(false)

// ============================================================
// 步骤管理
// ============================================================
const stepList = [
  { title: '上传全量发票基础信息表', desc: '上传Excel发票数据' },
  { title: '邮箱匹配', desc: '与邮件系统匹配核销' },
  { title: '手动匹配', desc: '多模态视觉识别' },
  { title: '报销申请', desc: '提交报销申请单' },
]
const activeStep = ref(0)

// ============================================================
// 查询条件 & 分页（步骤1）
// ============================================================
const filters = reactive({ keyword: '', invoice_source: '', invoice_type: '', verify_status: '', start_date: '', end_date: '' })
const dateRange = ref<string[]>([])
const pagination = reactive({ page: 1, pageSize: 20, total: 0 })

const invoiceSourceOptions = ['电子发票服务平台', '增值税发票管理系统', '税控盘开票', '税务UKey开票', '其他']
const invoiceTypeOptions = ['增值税专用发票', '增值税普通发票', '电子专用发票', '电子普通发票', '数电专票', '数电普票', '通行费电子发票']

// ============================================================
// 表格数据
// ============================================================
const loading = ref(false)
const tableData = ref<InvoiceDetailItem[]>([])

async function loadData() {
  loading.value = true
  try {
    const res = await getInvoiceDetails({
      keyword: filters.keyword || undefined,
      invoice_source: filters.invoice_source || undefined,
      invoice_type: filters.invoice_type || undefined,
      verify_status: filters.verify_status || undefined,
      start_date: filters.start_date || undefined,
      end_date: filters.end_date || undefined,
      page: pagination.page,
      page_size: pagination.pageSize,
    })
    tableData.value = res.items
    pagination.total = res.total
  } catch (e) { console.error(e) } finally { loading.value = false }
}

function handleSearch() { pagination.page = 1; loadData() }

function handleDateChange(val: string[] | null) {
  if (val && val.length === 2) { filters.start_date = val[0]; filters.end_date = val[1] }
  else { filters.start_date = ''; filters.end_date = '' }
  handleSearch()
}

// ============================================================
// 格式化
// ============================================================
function verifyStatusType(s?: string | null): 'success' | 'danger' | 'info' | 'warning' {
  if (s === '已核销') return 'success'
  if (s === '未匹配') return 'danger'
  return 'info'
}
function verifyStatusText(s?: string | null): string {
  if (s === '已核销') return '已核销'
  if (s === '未匹配') return '未匹配'
  return '待核销'
}
function formatAmount(val: string | number | null | undefined): string {
  if (val === null || val === undefined || val === '') return '-'
  const n = Number(val)
  if (Number.isNaN(n)) return String(val)
  return n.toFixed(2)
}
function formatTime(val?: string | null): string {
  if (!val) return '-'
  const d = new Date(val)
  if (Number.isNaN(d.getTime())) return val
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`
}

// ============================================================
// 上传对话框
// ============================================================
const uploadDialogVisible = ref(false)
const uploadRef = ref<UploadInstance>()
const uploadFileList = ref<UploadUserFile[]>([])
const selectedFile = ref<File | null>(null)
const uploading = ref(false)

function handleUpload() { uploadDialogVisible.value = true }
function handleFileChange(file: UploadFile, files: UploadUserFile[]) {
  if (!(file.name || '').toLowerCase().endsWith('.xlsx')) {
    ElMessage.error('仅支持 .xlsx 文件')
    uploadFileList.value = files.filter((f) => f.uid !== file.uid)
    selectedFile.value = null
    return
  }
  uploadFileList.value = files
  selectedFile.value = (file.raw as File) || null
}
function handleFileRemove(_file: UploadFile, files: UploadUserFile[]) { uploadFileList.value = files; selectedFile.value = null }
function handleExceed() { ElMessage.warning('仅支持上传一个文件，请先移除已选文件') }
function resetUploadDialog() { uploadFileList.value = []; selectedFile.value = null; uploadRef.value?.clearFiles() }

async function handleUploadSubmit() {
  if (!selectedFile.value) { ElMessage.warning('请先选择文件'); return }
  uploading.value = true
  try {
    const res = await uploadInvoiceDetail(selectedFile.value)
    ElMessage.success(res.skipped_count > 0 ? `成功导入 ${res.total_count} 条，跳过 ${res.skipped_count} 条重复` : `成功导入 ${res.total_count} 条记录`)
    uploadDialogVisible.value = false
    resetUploadDialog()
    await loadData()
    await loadUploadLogs()
  } catch (e) { console.error(e) } finally { uploading.value = false }
}

// ============================================================
// 核销
// ============================================================
const verifying = ref(false)
const verifyResult = ref<VerifyResult | null>(null)
const verifyResultVisible = ref(false)

async function handleVerify() {
  try { await ElMessageBox.confirm('确认对所有待核销记录执行核销操作？', '核销确认', { type: 'warning', confirmButtonText: '确认核销', cancelButtonText: '取消' }) } catch { return }
  verifying.value = true
  try {
    const res = await verifyInvoices()
    verifyResult.value = res
    verifyResultVisible.value = true
    ElMessage[res.matched_count > 0 ? 'success' : 'warning'](res.matched_count > 0 ? `核销完成，匹配 ${res.matched_count} 条` : '核销完成，未匹配到任何发票')
    await loadData()
    await loadVerifyRecords()
    await loadUnmatchedInvoices()
  } catch (e) { console.error(e) } finally { verifying.value = false }
}

// ============================================================
// 详情
// ============================================================
const detailVisible = ref(false)
const currentDetail = ref<InvoiceDetailItem | null>(null)
function showDetail(row: InvoiceDetailItem) { currentDetail.value = row; detailVisible.value = true }

// ============================================================
// 步骤2 - 邮箱配置
// ============================================================
const emailConfigs = ref<ReimbEmailConfig[]>([])
const emailConfigLoading = ref(false)
const testingId = ref<number | null>(null)
const emailDialogVisible = ref(false)
const emailEditing = ref(false)
const emailEditingId = ref<number | null>(null)
const emailSaving = ref(false)
const emailFormRef = ref<FormInstance>()
const emailForm = reactive({ email_address: '', imap_server: '', port: 993, password: '', use_ssl: true })
const emailRules: FormRules = {
  email_address: [{ required: true, message: '请输入邮箱', trigger: 'blur' }],
  imap_server: [{ required: true, message: '请输入IMAP服务器', trigger: 'blur' }],
  port: [{ required: true, message: '请输入端口', trigger: 'blur' }],
}

async function loadEmailConfigs() {
  emailConfigLoading.value = true
  try { emailConfigs.value = (await getReimbEmailConfigs()) || [] } catch { /* */ } finally { emailConfigLoading.value = false }
}

function openCreateEmail() {
  emailEditing.value = false; emailEditingId.value = null
  emailForm.email_address = ''; emailForm.imap_server = ''; emailForm.port = 993; emailForm.password = ''; emailForm.use_ssl = true
  emailDialogVisible.value = true
}
function openEditEmail(row: ReimbEmailConfig) {
  emailEditing.value = true; emailEditingId.value = row.id
  emailForm.email_address = row.email_address; emailForm.imap_server = row.imap_server; emailForm.port = row.port; emailForm.password = ''; emailForm.use_ssl = row.use_ssl
  emailDialogVisible.value = true
}

async function handleEmailSubmit() {
  if (!emailFormRef.value) return
  const valid = await emailFormRef.value.validate().then(() => true).catch(() => false)
  if (!valid) return
  emailSaving.value = true
  try {
    if (emailEditing.value && emailEditingId.value != null) {
      const payload: any = { email_address: emailForm.email_address, imap_server: emailForm.imap_server, port: emailForm.port, use_ssl: emailForm.use_ssl }
      if (emailForm.password) payload.password = emailForm.password
      await updateReimbEmailConfig(emailEditingId.value, payload)
      ElMessage.success('保存成功')
    } else {
      if (!emailForm.password) { ElMessage.warning('请输入密码'); emailSaving.value = false; return }
      await createReimbEmailConfig({ email_address: emailForm.email_address, imap_server: emailForm.imap_server, port: emailForm.port, password: emailForm.password, use_ssl: emailForm.use_ssl })
      ElMessage.success('添加成功')
    }
    emailDialogVisible.value = false
    await loadEmailConfigs()
  } catch { /* */ } finally { emailSaving.value = false }
}

async function handleDeleteEmail(row: ReimbEmailConfig) {
  try { await ElMessageBox.confirm(`确认删除邮箱「${row.email_address}」？`, '删除确认', { type: 'warning' }) } catch { return }
  try { await deleteReimbEmailConfig(row.id); ElMessage.success('已删除'); await loadEmailConfigs() } catch { /* */ }
}

async function handleTestConnection(row: ReimbEmailConfig) {
  testingId.value = row.id
  try {
    const res: ReimbEmailTestResult = await testReimbEmailConnection(row.id)
    res.success ? ElMessage.success('连接成功') : ElMessage.error(res.message || '连接失败')
  } catch { ElMessage.error('测试失败') } finally { testingId.value = null }
}

// ============================================================
// 步骤2 - 拉取邮件
// ============================================================
const fetching = ref(false)
const fetchDateRange = ref<string[]>([])
const emailMessages = ref<ReimbEmailMessage[]>([])
const emailMessagesLoading = ref(false)
const emailMsgPagination = reactive({ page: 1, pageSize: 10, total: 0 })

const invoiceDateRange = computed(() => {
  if (tableData.value.length === 0) return '暂无数据'
  const dates = tableData.value.map(i => i.invoice_date).filter(Boolean) as string[]
  if (dates.length === 0) return '暂无日期数据'
  dates.sort()
  return `${dates[0].substring(0, 10)} ~ ${dates[dates.length - 1].substring(0, 10)}`
})

async function loadEmailMessages() {
  emailMessagesLoading.value = true
  try {
    const res = await getReimbEmailMessages({ page: emailMsgPagination.page, page_size: emailMsgPagination.pageSize })
    emailMessages.value = res.items || []
    emailMsgPagination.total = res.total || 0
  } catch { /* */ } finally { emailMessagesLoading.value = false }
}

async function handleFetchEmails() {
  const activeConfigs = emailConfigs.value.filter(c => c.is_active)
  if (activeConfigs.length === 0) { ElMessage.warning('没有活跃的邮箱配置'); return }
  fetching.value = true
  try {
    const params: any = {}
    if (fetchDateRange.value && fetchDateRange.value.length === 2) {
      params.date_from = fetchDateRange.value[0]
      params.date_to = fetchDateRange.value[1]
    }
    let totalNew = 0
    for (const cfg of activeConfigs) {
      const res: ReimbEmailFetchResult = await fetchReimbEmails(cfg.id, params)
      totalNew += res.new_count || 0
    }
    ElMessage.success(`拉取完成，新增 ${totalNew} 封邮件`)
    await loadEmailMessages()
    await loadFetchLogs()
  } catch (e) { console.error(e) } finally { fetching.value = false }
}

// ============================================================
// 步骤3 - 未匹配发票
// ============================================================
const unmatchedInvoices = ref<InvoiceDetailItem[]>([])
const unmatchedLoading = ref(false)

async function loadUnmatchedInvoices() {
  unmatchedLoading.value = true
  try {
    const res = await getInvoiceDetails({ verify_status: '未匹配', page: 1, page_size: 100 })
    unmatchedInvoices.value = res.items
  } catch { /* */ } finally { unmatchedLoading.value = false }
}

// ============================================================
// 步骤3 - 手工匹配
// ============================================================
const manualMatchDialogVisible = ref(false)
const manualMatchTarget = ref<InvoiceDetailItem | null>(null)
const manualMatchFile = ref<File | null>(null)
const manualMatchFileList = ref<UploadUserFile[]>([])
const manualMatchUploadRef = ref<UploadInstance>()
const manualMatching = ref(false)
const manualMatchResultData = ref<ManualMatchResult | null>(null)

function openManualMatch(row: InvoiceDetailItem) {
  manualMatchTarget.value = row
  manualMatchFile.value = null
  manualMatchFileList.value = []
  manualMatchResultData.value = null
  manualMatchUploadRef.value?.clearFiles()
  manualMatchDialogVisible.value = true
}

function handleManualMatchFileChange(file: UploadFile, files: UploadUserFile[]) {
  const ext = (file.name || '').toLowerCase().split('.').pop()
  if (!['pdf', 'jpg', 'jpeg', 'png'].includes(ext || '')) {
    ElMessage.error('仅支持 PDF/JPG/PNG 文件')
    manualMatchFileList.value = files.filter(f => f.uid !== file.uid)
    manualMatchFile.value = null
    return
  }
  manualMatchFileList.value = files
  manualMatchFile.value = (file.raw as File) || null
}

function handleManualMatchFileRemove(_file: UploadFile, files: UploadUserFile[]) {
  manualMatchFileList.value = files
  manualMatchFile.value = null
}

async function handleManualMatchSubmit() {
  if (!manualMatchFile.value || !manualMatchTarget.value) return
  manualMatching.value = true
  manualMatchResultData.value = null
  try {
    const res = await manualMatchInvoice(manualMatchTarget.value.id, manualMatchFile.value)
    manualMatchResultData.value = res
    if (res.match_result === 'matched') {
      ElMessage.success('匹配成功！发票已核销')
      await loadUnmatchedInvoices()
      await loadData()
      await loadManualMatchRecords()
    }
  } catch (e) {
    console.error(e)
    ElMessage.error('识别请求失败，请重试')
  } finally {
    manualMatching.value = false
  }
}

// 报销申请记录
const reimbApplications = ref<any[]>([])
const reimbApplicationsLoading = ref(false)
const reimbApplicationsPagination = reactive({ page: 1, pageSize: 10, total: 0 })

async function loadReimbApplications() {
  reimbApplicationsLoading.value = true
  try {
    const res = await getReimburseApplications({ page: reimbApplicationsPagination.page, page_size: reimbApplicationsPagination.pageSize })
    reimbApplications.value = res.items || []
    reimbApplicationsPagination.total = res.total || 0
  } catch { /* */ } finally { reimbApplicationsLoading.value = false }
}

/** 导出报销申请PDF */
async function handleExportPDF(row: any) {
  try {
    row._exporting = true
    const res = await exportReimburseApplicationPdf(row.id)
    // 创建下载链接
    const blob = new Blob([res as any], { type: 'application/pdf' })
    const url = window.URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = `报销单_${row.reimburse_no}.pdf`
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    window.URL.revokeObjectURL(url)
    ElMessage.success('导出成功')
  } catch (e: any) {
    ElMessage.error(e?.message || '导出失败，请重试')
  } finally {
    row._exporting = false
  }
}

// 手工匹配记录
const manualMatchRecords = ref<ManualMatchRecordType[]>([])
const manualMatchRecordsLoading = ref(false)
const manualMatchRecordsPagination = reactive({ page: 1, pageSize: 10, total: 0 })

async function loadManualMatchRecords() {
  manualMatchRecordsLoading.value = true
  try {
    const res = await getManualMatchRecords({ page: manualMatchRecordsPagination.page, page_size: manualMatchRecordsPagination.pageSize })
    manualMatchRecords.value = res.items || []
    manualMatchRecordsPagination.total = res.total || 0
  } catch { /* */ } finally { manualMatchRecordsLoading.value = false }
}

// ============================================================
// 步骤4 - 已核销发票
// ============================================================
const matchedInvoices = ref<InvoiceDetailItem[]>([])
const matchedLoading = ref(false)
const matchedPagination = reactive({ page: 1, pageSize: 20, total: 0 })
const matchedTableRef = ref<any>(null)
const submittingReimburse = ref(false)

// 步骤4 已核销发票表格客户端过滤
const matchedFilter = reactive<{ dateRange: string[] | null; sellerName: string; invoiceType: string; matchMethod: string; reimburseStatus: string }>({
  dateRange: null,
  sellerName: '',
  invoiceType: '',
  matchMethod: '',
  reimburseStatus: ''
})

const matchedInvoiceTypeOptions = computed(() => {
  const set = new Set<string>()
  matchedInvoices.value.forEach((it) => { if (it.invoice_type) set.add(String(it.invoice_type)) })
  // 兜底常见票种
  if (set.size === 0) {
    return ['数电发票（普通）', '数电发票（增值税专用）', '增值税专用发票', '增值税普通发票', '电子普通发票']
  }
  return Array.from(set)
})

const matchedMethodOptions = computed(() => {
  const set = new Set<string>()
  matchedInvoices.value.forEach((it) => { if (it.match_method) set.add(String(it.match_method)) })
  if (set.size === 0) return ['邮箱匹配', '手工匹配']
  return Array.from(set)
})

const filteredMatchedInvoices = computed(() => {
  const { dateRange, sellerName, invoiceType, matchMethod, reimburseStatus } = matchedFilter
  const startDate = dateRange && dateRange[0] ? dateRange[0] : ''
  const endDate = dateRange && dateRange[1] ? dateRange[1] : ''
  const sellerKey = sellerName.trim().toLowerCase()
  return matchedInvoices.value.filter((row) => {
    if (startDate || endDate) {
      const d = (row.invoice_date || '').substring(0, 10)
      if (!d) return false
      if (startDate && d < startDate) return false
      if (endDate && d > endDate) return false
    }
    if (sellerKey) {
      const seller = String(row.seller_name || '').toLowerCase()
      if (!seller.includes(sellerKey)) return false
    }
    if (invoiceType && row.invoice_type !== invoiceType) return false
    if (matchMethod && row.match_method !== matchMethod) return false
    if (reimburseStatus && row.reimburse_status !== reimburseStatus) return false
    return true
  })
})

const matchedFilterActive = computed(() => {
  const { dateRange, sellerName, invoiceType, matchMethod, reimburseStatus } = matchedFilter
  return Boolean((dateRange && (dateRange[0] || dateRange[1])) || sellerName || invoiceType || matchMethod || reimburseStatus)
})

const matchedPaginationTotal = computed(() => {
  return matchedFilterActive.value ? filteredMatchedInvoices.value.length : matchedPagination.total
})

function handleMatchedFilterSearch() {
  // 客户端过滤无需请求后端，computed 自动响应
}

function handleMatchedFilterReset() {
  matchedFilter.dateRange = null
  matchedFilter.sellerName = ''
  matchedFilter.invoiceType = ''
  matchedFilter.matchMethod = ''
  matchedFilter.reimburseStatus = ''
}

async function loadMatchedInvoices() {
  matchedLoading.value = true
  try {
    const res = await getInvoiceDetails({ verify_status: '已核销', page: matchedPagination.page, page_size: matchedPagination.pageSize })
    matchedInvoices.value = res.items
    matchedPagination.total = res.total
  } catch { /* */ } finally { matchedLoading.value = false }
}

async function handleSubmitReimburse() {
  const selection = matchedTableRef.value?.getSelectionRows() || []
  if (selection.length === 0) {
    ElMessage.warning('请先选择要提交报销的发票')
    return
  }
  // 只选择待报销的发票
  const pendingItems = selection.filter((item: InvoiceDetailItem) => item.reimburse_status !== '已报销')
  if (pendingItems.length === 0) {
    ElMessage.warning('选中的发票均已报销')
    return
  }
  // 打开报销申请模态窗口
  reimburseSelectedInvoices.value = pendingItems
  reimburseFormData.reimburse_date = new Date().toISOString().substring(0, 10)
  reimburseFormData.department = ''
  reimburseFormData.category = ''
  reimburseFormData.reason = ''
  reimburseFormData.remark = ''
  // 按"货物或应税劳务名称"分组汇总
  const groupMap = new Map<string, { date: string; content: string; receipt_count: number; amount: number; remarks: Set<string> }>()
  pendingItems.forEach((item: InvoiceDetailItem) => {
    const groupKey = item.goods_or_service_name && String(item.goods_or_service_name).trim() !== '' ? String(item.goods_or_service_name) : '其他'
    const invoiceDate = item.invoice_date ? String(item.invoice_date).substring(0, 10) : ''
    const amountNum = Number(item.total_amount) || 0
    const remarkStr = item.remark ? String(item.remark).trim() : ''
    if (!groupMap.has(groupKey)) {
      groupMap.set(groupKey, {
        date: invoiceDate,
        content: groupKey,
        receipt_count: 1,
        amount: amountNum,
        remarks: new Set<string>(remarkStr ? [remarkStr] : [])
      })
    } else {
      const g = groupMap.get(groupKey)!
      if (invoiceDate && (!g.date || invoiceDate < g.date)) {
        g.date = invoiceDate
      }
      g.receipt_count += 1
      g.amount += amountNum
      if (remarkStr) g.remarks.add(remarkStr)
    }
  })
  const aggregated = Array.from(groupMap.values()).map(g => ({
    date: g.date,
    content: g.content,
    receipt_count: g.receipt_count,
    amount: Number(g.amount.toFixed(2)),
    remark: Array.from(g.remarks).join('、')
  }))
  reimburseItems.value = aggregated.length > 0 ? aggregated : [{ date: '', content: '', receipt_count: 1, amount: 0, remark: '' }]
  reimburseDialogVisible.value = true
}

// ============================================================
// 步骤4 - 报销申请弹窗
// ============================================================
const reimburseDialogVisible = ref(false)
const reimburseSelectedInvoices = ref<InvoiceDetailItem[]>([])
const reimburseFormRef = ref<FormInstance>()
const reimburseFormData = reactive({
  reimburse_date: '',
  department: '',
  category: '',
  reason: '',
  remark: '',
})

// 报销明细行
interface ReimburseItem {
  date: string
  content: string
  receipt_count: number
  amount: number
  remark: string
}

const reimburseItems = ref<ReimburseItem[]>([
  { date: '', content: '', receipt_count: 1, amount: 0, remark: '' }
])

function addReimburseRow() {
  reimburseItems.value.push({ date: '', content: '', receipt_count: 1, amount: 0, remark: '' })
}

function removeReimburseRow(index: number) {
  if (reimburseItems.value.length <= 1) {
    ElMessage.warning('至少保留一行')
    return
  }
  reimburseItems.value.splice(index, 1)
}

const reimburseItemsTotal = computed(() => {
  const total = reimburseItems.value.reduce((sum, item) => sum + (Number(item.amount) || 0), 0)
  return total.toFixed(2)
})

const departmentOptions = ['财务部', '技术部', '市场部', '人事部', '行政部', '研发部']

const reimburseRules: FormRules = {
  reimburse_date: [{ required: true, message: '请选择报销日期', trigger: 'change' }],
  department: [{ required: true, message: '请选择报销部门', trigger: 'change' }],
}

const reimburseTotal = computed(() => {
  const total = reimburseSelectedInvoices.value.reduce((sum, item) => {
    const amt = Number(item.total_amount)
    return sum + (Number.isNaN(amt) ? 0 : amt)
  }, 0)
  return total.toFixed(2)
})

async function handleReimburseSubmit() {
  if (!reimburseFormRef.value) return
  const valid = await reimburseFormRef.value.validate().then(() => true).catch(() => false)
  if (!valid) return

  submittingReimburse.value = true
  try {
    const ids = reimburseSelectedInvoices.value.map(item => item.id)
    const summary = reimburseItems.value.map(i => i.content).filter(Boolean).join('、') || '报销申请'
    const res = await createReimburseApplication({
      reimburse_date: reimburseFormData.reimburse_date,
      department: reimburseFormData.department,
      category: summary,
      reason: summary,
      remark: reimburseFormData.remark || undefined,
      invoice_ids: ids,
      detail_items: reimburseItems.value.map(i => ({
        date: i.date,
        content: i.content,
        receipt_count: i.receipt_count,
        amount: i.amount,
        remark: i.remark,
      })),
    })
    ElMessage.success(`报销申请提交成功！报销单编号：${res.reimburse_no}`)
    reimburseDialogVisible.value = false
    await loadMatchedInvoices()
    await loadReimbApplications()
  } catch (e) {
    console.error(e)
    ElMessage.error('报销申请提交失败，请重试')
  } finally {
    submittingReimburse.value = false
  }
}

// ============================================================
// 步骤状态
// ============================================================
const currentStep = computed(() => {
  if (pagination.total <= 0) return 0
  if (verifyRecordsPagination.total <= 0) return 1
  return 2
})

// ============================================================
// 底部记录 - 核销记录
// ============================================================
const verifyRecords = ref<any[]>([])
const verifyRecordsLoading = ref(false)
const verifyRecordsPagination = reactive({ page: 1, pageSize: 10, total: 0 })
const unmatchedDialogVisible = ref(false)
const currentUnmatchedList = ref<string[]>([])

async function loadVerifyRecords() {
  verifyRecordsLoading.value = true
  try {
    const res = await getReimbursementRecords({ page: verifyRecordsPagination.page, pageSize: verifyRecordsPagination.pageSize })
    verifyRecords.value = res.items || []
    verifyRecordsPagination.total = res.total || 0
  } catch { /* */ } finally { verifyRecordsLoading.value = false }
}

function showUnmatched(record: any) {
  currentUnmatchedList.value = record.unmatched_details || []
  unmatchedDialogVisible.value = true
}

// ============================================================
// 底部记录 - 上传记录
// ============================================================
const uploadLogs = ref<any[]>([])
const uploadLogsLoading = ref(false)
const uploadLogsPagination = reactive({ page: 1, pageSize: 10, total: 0 })

async function loadUploadLogs() {
  uploadLogsLoading.value = true
  try {
    const res = await getUploadLogs({ page: uploadLogsPagination.page, page_size: uploadLogsPagination.pageSize })
    uploadLogs.value = res.items || []
    uploadLogsPagination.total = res.total || 0
  } catch { /* */ } finally { uploadLogsLoading.value = false }
}

// ============================================================
// 底部记录 - 拉取记录
// ============================================================
const fetchLogs = ref<ReimbEmailFetchLog[]>([])
const fetchLogsLoading = ref(false)
const fetchLogsPagination = reactive({ page: 1, pageSize: 10, total: 0 })

async function loadFetchLogs() {
  fetchLogsLoading.value = true
  try {
    const res = await getReimbEmailFetchLogs({ page: fetchLogsPagination.page, page_size: fetchLogsPagination.pageSize })
    fetchLogs.value = res.items || []
    fetchLogsPagination.total = res.total || 0
  } catch { /* */ } finally { fetchLogsLoading.value = false }
}

// ============================================================
// 自动填充拉取日期范围
// ============================================================
watch(
  [activeStep, tableData],
  () => {
    if (activeStep.value === 1 && (!fetchDateRange.value || fetchDateRange.value.length === 0)) {
      const dates = tableData.value.map(i => i.invoice_date).filter(Boolean) as string[]
      if (dates.length > 0) {
        dates.sort()
        fetchDateRange.value = [dates[0].substring(0, 10), dates[dates.length - 1].substring(0, 10)]
      }
    }
  },
  { immediate: true }
)

watch(activeStep, (newStep) => {
  if (newStep === 2) {
    loadUnmatchedInvoices()
  } else if (newStep === 3) {
    loadMatchedInvoices()
    loadReimbApplications()
  }
})

// ============================================================
// 生命周期
// ============================================================
onMounted(() => {
  loadData()
  loadVerifyRecords()
  loadUploadLogs()
  loadEmailConfigs()
  loadEmailMessages()
  loadFetchLogs()
  loadUnmatchedInvoices()
  loadManualMatchRecords()
  loadMatchedInvoices()
  loadReimbApplications()
})
</script>

<style scoped>
.reimbursement-page { padding: 0; }
.steps-card :deep(.el-step__head), .steps-card :deep(.el-step__title) { cursor: pointer; }
.toolbar-actions { display: flex; gap: 8px; align-items: center; margin-bottom: 12px; }
.toolbar-filters { display: flex; gap: 8px; align-items: center; flex-wrap: wrap; }
.pagination-wrap { margin-top: 16px; display: flex; justify-content: flex-end; }
.card-header { display: flex; align-items: center; justify-content: space-between; gap: 12px; }
.card-header__title { font-size: 15px; font-weight: 600; color: #303133; }
.detail-upload :deep(.el-upload-dragger) { padding: 32px 20px; }
.result-number { font-weight: 700; font-size: 16px; }
.result-success { color: #67c23a; }
.result-danger { color: #f56c6c; }
.unmatched-area { margin-top: 16px; padding: 12px 16px; background: #fef0f0; border-radius: 6px; border: 1px solid #fde2e2; }
.unmatched-title { font-size: 13px; color: var(--el-text-color-primary); margin-bottom: 8px; font-weight: 500; }
.unmatched-list { display: flex; flex-wrap: wrap; gap: 6px; }

/* 步骤节点颜色区分 */
.steps-card :deep(.el-step:nth-child(1) .el-step__title) {
  color: #409EFF !important;
}
.steps-card :deep(.el-step:nth-child(1) .el-step__head.is-finish .el-step__icon) {
  border-color: #409EFF;
  background-color: #409EFF;
  color: #fff;
}
.steps-card :deep(.el-step:nth-child(1) .el-step__head.is-process .el-step__icon) {
  border-color: #409EFF;
  background-color: #409EFF;
  color: #fff;
}
.steps-card :deep(.el-step:nth-child(1) .el-step__head.is-wait .el-step__icon) {
  border-color: #409EFF;
  background-color: #409EFF;
  color: #fff;
}

.steps-card :deep(.el-step:nth-child(2) .el-step__title) {
  color: #67C23A !important;
}
.steps-card :deep(.el-step:nth-child(2) .el-step__head.is-finish .el-step__icon) {
  border-color: #67C23A;
  background-color: #67C23A;
  color: #fff;
}
.steps-card :deep(.el-step:nth-child(2) .el-step__head.is-process .el-step__icon) {
  border-color: #67C23A;
  background-color: #67C23A;
  color: #fff;
}
.steps-card :deep(.el-step:nth-child(2) .el-step__head.is-wait .el-step__icon) {
  border-color: #67C23A;
  background-color: #67C23A;
  color: #fff;
}

.steps-card :deep(.el-step:nth-child(3) .el-step__title) {
  color: #E6A23C !important;
}
.steps-card :deep(.el-step:nth-child(3) .el-step__head.is-finish .el-step__icon) {
  border-color: #E6A23C;
  background-color: #E6A23C;
  color: #fff;
}
.steps-card :deep(.el-step:nth-child(3) .el-step__head.is-process .el-step__icon) {
  border-color: #E6A23C;
  background-color: #E6A23C;
  color: #fff;
}
.steps-card :deep(.el-step:nth-child(3) .el-step__head.is-wait .el-step__icon) {
  border-color: #E6A23C;
  background-color: #E6A23C;
  color: #fff;
}

.steps-card :deep(.el-step:nth-child(4) .el-step__title) {
  color: #9B59B6 !important;
}
.steps-card :deep(.el-step:nth-child(4) .el-step__head.is-finish .el-step__icon) {
  border-color: #9B59B6;
  background-color: #9B59B6;
  color: #fff;
}
.steps-card :deep(.el-step:nth-child(4) .el-step__head.is-process .el-step__icon) {
  border-color: #9B59B6;
  background-color: #9B59B6;
  color: #fff;
}
.steps-card :deep(.el-step:nth-child(4) .el-step__head.is-wait .el-step__icon) {
  border-color: #9B59B6;
  background-color: #9B59B6;
  color: #fff;
}

.steps-card :deep(.el-step:nth-child(1) .el-step__description) { color: #409EFF !important; opacity: 0.8; }
.steps-card :deep(.el-step:nth-child(2) .el-step__description) { color: #67C23A !important; opacity: 0.8; }
.steps-card :deep(.el-step:nth-child(3) .el-step__description) { color: #E6A23C !important; opacity: 0.8; }
.steps-card :deep(.el-step:nth-child(4) .el-step__description) { color: #9B59B6 !important; opacity: 0.8; }
</style>
