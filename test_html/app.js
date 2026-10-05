// Quản lý trạng thái giao diện kiểm thử OCR Service
document.addEventListener("DOMContentLoaded", () => {
  const apiUrlInput = document.getElementById("apiUrlInput");
  const btnCheckHealth = document.getElementById("btnCheckHealth");
  const presetSelect = document.getElementById("presetSelect");
  const targetFieldsInput = document.getElementById("targetFieldsInput");
  const serverPill = document.getElementById("serverPill");
  const serverStatusText = document.getElementById("serverStatusText");

  // Xử lý thay đổi Preset Profile
  if (presetSelect && targetFieldsInput) {
    presetSelect.addEventListener("change", () => {
      const val = presetSelect.value;
      if (val === "song_license") {
        targetFieldsInput.style.display = "block";
        targetFieldsInput.value = "license_type,copyright_owner,distributor,contract_id,issue_date,expiry_date";
      } else if (val === "profile") {
        targetFieldsInput.style.display = "block";
        targetFieldsInput.value = "full_name,dob,id_card_no,address,email,phone_number";
      } else if (val === "invoice") {
        targetFieldsInput.style.display = "block";
        targetFieldsInput.value = "document_no,date,tax_code,total_amount,customer_name";
      } else if (val === "all") {
        targetFieldsInput.style.display = "none";
        targetFieldsInput.value = "";
      } else if (val === "custom") {
        targetFieldsInput.style.display = "block";
        targetFieldsInput.focus();
      }
    });
  }


  const dropzone = document.getElementById("dropzone");
  const fileInput = document.getElementById("fileInput");
  const dropzonePrompt = document.getElementById("dropzonePrompt");
  const filePreviewCard = document.getElementById("filePreviewCard");
  const previewFileName = document.getElementById("previewFileName");
  const previewFileSize = document.getElementById("previewFileSize");
  const btnRemoveFile = document.getElementById("btnRemoveFile");
  const btnUpload = document.getElementById("btnUpload");
  const btnSpinner = document.getElementById("btnSpinner");

  const emptyState = document.getElementById("emptyState");
  const loadingState = document.getElementById("loadingState");
  const resultContent = document.getElementById("resultContent");
  const fieldsGrid = document.getElementById("fieldsGrid");
  const docUuid = document.getElementById("docUuid");
  const rawTextViewer = document.getElementById("rawTextViewer");
  const btnCopyRawText = document.getElementById("btnCopyRawText");
  const jsonViewer = document.getElementById("jsonViewer");
  const btnCopyJson = document.getElementById("btnCopyJson");

  const tagEngine = document.getElementById("tagEngine");
  const tagTime = document.getElementById("tagTime");
  const tagConfidence = document.getElementById("tagConfidence");

  let selectedFile = null;

  // 1. Kiểm tra Health Check của server
  async function checkServerHealth() {
    serverStatusText.textContent = "Đang kiểm tra kết nối...";
    serverPill.className = "server-status-pill";

    // Lấy host gốc từ apiUrlInput
    const urlVal = apiUrlInput.value.trim();
    let healthUrl = "http://localhost:8001/health";
    try {
      const parsed = new URL(urlVal);
      healthUrl = `${parsed.origin}/health`;
    } catch {
      healthUrl = "http://localhost:8001/health";
    }

    try {
      const res = await fetch(healthUrl, { method: "GET" });
      if (res.ok) {
        const data = await res.json();
        if (data.status === "UP") {
          serverPill.className = "server-status-pill online";
          serverStatusText.textContent = "Server Online (Status: UP)";
          return true;
        }
      }
      throw new Error("Status not UP");
    } catch {
      // Thử fallback sang port 8000 nếu port 8001 không được
      try {
        const fallbackRes = await fetch("http://localhost:8000/health");
        if (fallbackRes.ok) {
          apiUrlInput.value = "http://localhost:8000/api/v1/ocr/pdf";
          serverPill.className = "server-status-pill online";
          serverStatusText.textContent = "Server Online (Port 8000)";
          return true;
        }
      } catch {
        // Cả 2 đều offline
      }

      serverPill.className = "server-status-pill offline";
      serverStatusText.textContent = "Không kết nối được Server";
      return false;
    }
  }

  // Khởi động kiểm tra ngay
  checkServerHealth();
  btnCheckHealth.addEventListener("click", checkServerHealth);

  // 2. Kéo thả & Chọn File
  function handleFileSelection(file) {
    if (!file) return;

    if (!file.name.toLowerCase().endsWith(".pdf")) {
      alert("Chỉ chấp nhận file định dạng PDF (.pdf)!");
      return;
    }

    if (file.size > 10 * 1024 * 1024) {
      alert("Dung lượng file vượt quá giới hạn 10MB!");
      return;
    }

    selectedFile = file;
    previewFileName.textContent = file.name;
    previewFileSize.textContent = formatBytes(file.size);

    dropzonePrompt.classList.add("hidden");
    filePreviewCard.classList.remove("hidden");
    btnUpload.disabled = false;
  }

  function clearSelectedFile(e) {
    if (e) e.stopPropagation();
    selectedFile = null;
    fileInput.value = "";
    dropzonePrompt.classList.remove("hidden");
    filePreviewCard.classList.add("hidden");
    btnUpload.disabled = true;
  }

  btnRemoveFile.addEventListener("click", clearSelectedFile);

  fileInput.addEventListener("change", (e) => {
    if (e.target.files.length > 0) {
      handleFileSelection(e.target.files[0]);
    }
  });

  // Drag and drop events
  ["dragenter", "dragover"].forEach((eventName) => {
    dropzone.addEventListener(eventName, (e) => {
      e.preventDefault();
      e.stopPropagation();
      dropzone.classList.add("dragover");
    });
  });

  ["dragleave", "drop"].forEach((eventName) => {
    dropzone.addEventListener(eventName, (e) => {
      e.preventDefault();
      e.stopPropagation();
      dropzone.classList.remove("dragover");
    });
  });

  dropzone.addEventListener("drop", (e) => {
    const dt = e.dataTransfer;
    if (dt.files && dt.files.length > 0) {
      handleFileSelection(dt.files[0]);
    }
  });

  // 3. Upload và Xử Lý OCR
  btnUpload.addEventListener("click", async () => {
    if (!selectedFile) return;

    const apiUrl = apiUrlInput.value.trim();
    if (!apiUrl) {
      alert("Vui lòng nhập API Endpoint hợp lệ!");
      return;
    }

    // Hiển thị loading
    btnUpload.disabled = true;
    btnSpinner.classList.remove("hidden");
    emptyState.classList.add("hidden");
    resultContent.classList.add("hidden");
    loadingState.classList.remove("hidden");

    // Ẩn metrics tags cũ
    tagEngine.classList.add("hidden");
    tagTime.classList.add("hidden");
    tagConfidence.classList.add("hidden");

    const formData = new FormData();
    formData.append("file", selectedFile);
    const targetFieldsVal = targetFieldsInput ? targetFieldsInput.value.trim() : "";
    if (targetFieldsVal) {
      formData.append("target_fields", targetFieldsVal);
    }

    const startTime = performance.now();

    try {
      const response = await fetch(apiUrl, {
        method: "POST",
        body: formData,
      });

      const elapsed = Math.round(performance.now() - startTime);
      const data = await response.json();

      loadingState.classList.add("hidden");

      if (response.ok && data.success) {
        displayResults(data, elapsed);
      } else {
        displayError(data.message || "Xử lý thất bại", data.error_code || response.status);
      }
    } catch (err) {
      loadingState.classList.add("hidden");
      displayError(`Không thể gửi request đến server: ${err.message}`, "NETWORK_ERROR");
    } finally {
      btnUpload.disabled = false;
      btnSpinner.classList.add("hidden");
    }
  });

  // 4. Hiển thị kết quả trích xuất
  function displayResults(data, elapsedMs) {
    resultContent.classList.remove("hidden");

    // Metrics tags
    tagTime.textContent = `${elapsedMs} ms`;
    tagTime.classList.remove("hidden");

    const conf = data.confidence !== undefined ? Math.round(data.confidence * 100) : 100;
    tagConfidence.textContent = `Confidence: ${conf}%`;
    tagConfidence.classList.remove("hidden");

    // Đoán hoặc dùng trực tiếp engine trả về
    let engineName = "⚡ Direct Text (PyMuPDF)";
    if (data.ocr_engine === "paddleocr") {
      engineName = "🔍 PaddleOCR 200 DPI";
    } else if (data.ocr_engine === "direct_text") {
      engineName = "⚡ Direct Text (PyMuPDF)";
    } else if (elapsedMs >= 200) {
      engineName = "🔍 PaddleOCR 200 DPI";
    }
    tagEngine.textContent = engineName;
    tagEngine.classList.remove("hidden");

    // UUID
    docUuid.textContent = `UUID: ${data.document_uuid || "N/A"}`;

    // Render Fields Grid
    fieldsGrid.innerHTML = "";
    const fields = data.extracted_fields || {};
    const fieldKeys = Object.keys(fields);

    const fieldLabels = {
      // Bản quyền & Giấy phép bài hát (song_licenses)
      license_type: "Loại Bản Quyền / Giấy Phép",
      copyright_owner: "Chủ Sở Hữu Quyền Tác Giả",
      distributor: "Đơn Vị Phân Phối",
      contract_id: "Mã Hợp Đồng (Contract ID)",
      issue_date: "Ngày Cấp / Bắt Đầu",
      expiry_date: "Ngày Hết Hạn",
      // Thông tin cá nhân / hồ sơ
      full_name: "Họ và Tên",
      dob: "Ngày Sinh",
      id_card_no: "Số CCCD / CMND",
      address: "Địa Chỉ",
      email: "Email",
      phone_number: "Số Điện Thoại",
      // Hóa đơn & chứng từ
      title: "Tiêu Đề Văn Bản",
      document_no: "Số Hóa Đơn / Văn Bản",
      date: "Ngày Phát Hành",
      tax_code: "Mã Số Thuế (MST)",
      total_amount: "Tổng Tiền Thanh Toán",
      customer_name: "Khách Hàng / Đơn Vị Mua",
    };

    if (fieldKeys.length === 0) {
      fieldsGrid.innerHTML = `
        <div style="grid-column: 1 / -1; padding: 20px; text-align: center; color: var(--text-muted); font-size: 13px;">
          (Không tìm thấy các trường thông tin theo mẫu, vui lòng xem văn bản đầy đủ bên dưới)
        </div>
      `;
    } else {
      fieldKeys.forEach((key) => {
        let val = fields[key];
        if (key === "total_amount" && typeof val === "number") {
          val = new Intl.NumberFormat("vi-VN", { style: "currency", currency: "VND" }).format(val);
        }

        const isHighlight = ["document_no", "tax_code", "total_amount", "id_card_no", "phone_number", "email", "contract_id", "license_type"].includes(key);


        const box = document.createElement("div");
        box.className = "field-box";
        box.innerHTML = `
          <div class="field-box-label">${fieldLabels[key] || key.replace(/_/g, " ").toUpperCase()}</div>
          <div class="field-box-value ${isHighlight ? "highlight" : ""}">${escapeHtml(String(val))}</div>
        `;
        fieldsGrid.appendChild(box);
      });
    }

    // Render Raw Extracted Text
    if (rawTextViewer) {
      rawTextViewer.textContent = data.raw_text || "(Không có text trích xuất)";
    }

    // Render Raw JSON
    jsonViewer.textContent = JSON.stringify(data, null, 2);
  }

  // 5. Hiển thị lỗi
  function displayError(message, errorCode) {
    resultContent.classList.remove("hidden");
    fieldsGrid.innerHTML = `
      <div style="grid-column: 1 / -1; padding: 24px; background: rgba(239, 68, 68, 0.1); border: 1px solid rgba(239, 68, 68, 0.3); border-radius: var(--radius-sm); color: #fca5a5;">
        <div style="font-weight: 700; font-size: 14px; margin-bottom: 4px;">❌ Lỗi Xử Lý [${escapeHtml(String(errorCode))}]</div>
        <div style="font-size: 13px;">${escapeHtml(message)}</div>
      </div>
    `;
    docUuid.textContent = "Thao tác không thành công";
    if (rawTextViewer) {
      rawTextViewer.textContent = "(Lỗi khi xử lý tài liệu)";
    }
    jsonViewer.textContent = JSON.stringify({ success: false, error_code: errorCode, message }, null, 2);
  }

  // Copy Raw Text button
  if (btnCopyRawText) {
    btnCopyRawText.addEventListener("click", () => {
      navigator.clipboard.writeText(rawTextViewer.textContent).then(() => {
        const orig = btnCopyRawText.textContent;
        btnCopyRawText.textContent = "Đã Sao Chép!";
        setTimeout(() => (btnCopyRawText.textContent = orig), 2000);
      });
    });
  }

  // Copy JSON button
  btnCopyJson.addEventListener("click", () => {
    navigator.clipboard.writeText(jsonViewer.textContent).then(() => {
      const orig = btnCopyJson.textContent;
      btnCopyJson.textContent = "Đã Sao Chép!";
      setTimeout(() => (btnCopyJson.textContent = orig), 2000);
    });
  });


  // Helper
  function formatBytes(bytes) {
    if (bytes === 0) return "0 Bytes";
    const k = 1024;
    const sizes = ["Bytes", "KB", "MB"];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + " " + sizes[i];
  }

  function escapeHtml(str) {
    return str
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#039;");
  }
});
