CREATE OR ALTER FUNCTION [dbo].[fn_DetectLanguage](@input_str NVARCHAR(4000))
RETURNS NVARCHAR(20)
AS
BEGIN
    -- 检测当前字段文字是否是本地文字
    -- it_zzy 2026-7-28
    -- 2026-11-06 修正：
    --   1) 越南判定统一返回 N'越南文'（与函数其它分支、以及所有调用方 =N'越南文' 对齐，
    --      否则新块返回 N'越南语' 会让现有 WHERE fn=e_name='越南文' 的查询漏掉 Phạm/Nguyễn 等人）；
    --   2) 优先级2 声调清单补全「帽/短/horn + 声调」复合字（ế ệ ố ộ ứ ự ấ ầ ắ ằ ...），
    --      避免极端情况（如只有 ễ 的姓氏 Mễ）漏判。

    -- 优先级1：越南独有字母（ăâđêôơư）
    IF @input_str LIKE N'%[ăâđêôơưĂÂĐÊÔƠƯ]%'
    BEGIN
        RETURN N'越南文'
    END
    -- 优先级2：越南声调字符（含帽/短/horn+声调复合字），且无中文/俄文
    ELSE IF @input_str LIKE N'%[áàảãạéèẻẽẹíìỉĩịóòỏõọúùủũụýỳỷỹỵÁÀẢÃẠÉÈẺẼẸÍÌỈĨỊÓÒỎÕỌÚÙỦŨỤÝỲỶỸỴẤẦẨẪẬẮẰẲẴẶẾỀỂỄỆỐỒỔỖỘỚỜỞỠỢỨỪỬỮỰ]%'
        AND NOT (@input_str LIKE N'%[一-龥]%' OR @input_str LIKE N'%[А-Яа-я]%')
    BEGIN
        RETURN N'越南文'
    END

    DECLARE @i INT = 1;
    DECLARE @len INT = LEN(@input_str);
    DECLARE @ch NCHAR(1);
    DECLARE @unicode INT;

    DECLARE @has_thai BIT = 0;
    DECLARE @has_vn BIT = 0;
    DECLARE @has_cn BIT = 0;
    DECLARE @has_arabic BIT = 0;
    DECLARE @has_tagalog BIT = 0;

    WHILE @i <= @len
    BEGIN
        SET @ch = SUBSTRING(@input_str, @i, 1);
        SET @unicode = UNICODE(@ch);

        -- 1.泰文
        IF @unicode BETWEEN 3584 AND 3711
        BEGIN
            SET @has_thai = 1;
            BREAK;
        END

        -- 2.越南语声调扩展字母（优先级高于中文）
        IF (@unicode BETWEEN 192 AND 214)
            OR (@unicode BETWEEN 216 AND 246)
            OR (@unicode BETWEEN 248 AND 495)
        BEGIN
            SET @has_vn = 1;
            BREAK;
        END

        -- 3.中文 CJK汉字
        IF @unicode BETWEEN 19968 AND 40895
        BEGIN
            SET @has_cn = 1;
            BREAK;
        END

        -- 4.阿拉伯文（沙特）
        IF @unicode BETWEEN 1536 AND 1791
        BEGIN
            SET @has_arabic = 1;
            BREAK;
        END

        -- 5.菲律宾文特征字符 ñ
        IF @unicode = 241
        BEGIN
            SET @has_tagalog = 1;
            BREAK;
        END

        SET @i = @i + 1;
    END

    -- 按优先级返回结果
    IF @has_thai = 1
        RETURN N'泰文'
    ELSE IF @has_vn = 1
        RETURN N'越南文'
    ELSE IF @has_cn = 1
        RETURN N'中文'
    ELSE IF @has_arabic = 1
        RETURN N'阿拉伯文(沙特)'
    ELSE IF @has_tagalog = 1
        RETURN N'菲律宾文'
    ELSE
        RETURN N'英文'
END
