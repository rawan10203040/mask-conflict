```python
import streamlit as st
import polars as pl
import io
import zipfile
import time


# ============================================================
# PAGE CONFIGURATION
# ============================================================

st.set_page_config(
    page_title="Collect & 9999 Processor",
    page_icon="📊",
    layout="wide"
)


# ============================================================
# CONFIGURATION
# ============================================================

ITEMID_COLUMN = "ItemId"
ITEMTYPE_COLUMN = "ItemType"

PART_COLUMN = "PartNumber"

FIRST_COMPANY_COLUMN = "PartCompanyName"
FIRST_JOIN_COLUMN = "PartNumberPartCompanyName"

SECOND_COMPANY_COLUMN = "CompanyName"
SECOND_JOIN_COLUMN = "PartNumberCompanyName"

DIE_FAMILY_COLUMN = "DieFamily"

MAX_ROWS_PER_FILE = 1000000

FIRST_SEARCH_COLUMNS = [
    "DistinctValues",
    "ItemName"
]

FIRST_SEARCH_VALUE = "-9999999999"

DIE_FAMILY_SEARCH_VALUE = "99999999"


# ============================================================
# HELPER FUNCTION
# ============================================================

def normalize_column(column_name):

    return (
        pl.col(column_name)
        .cast(pl.Utf8, strict=False)
        .fill_null("")
        .str.strip_chars()
        .str.to_uppercase()
    )


# ============================================================
# READ EXCEL FILE
# ============================================================

def read_excel_file(uploaded_file):

    try:

        return pl.read_excel(
            io.BytesIO(
                uploaded_file.getvalue()
            )
        )

    except Exception as e:

        raise Exception(
            f"Error reading "
            f"{uploaded_file.name}: {e}"
        )


# ============================================================
# MAIN APPLICATION
# ============================================================

st.title("📊 Collect & 9999 Processor")

st.write(
    """
    Upload the All Input files and Low Priority files.
    The application will search for `-9999999999` and `99999999`,
    remove the required rows, and generate the final output files.
    """
)


# ============================================================
# STEP 1
# UPLOAD ALL INPUT FILES
# ============================================================

st.header("Step 1 - Upload All Input Files")

uploaded_item_files = st.file_uploader(
    "Upload All Input Excel Files",
    type=["xlsx"],
    accept_multiple_files=True,
    key="all_input_files"
)


# ============================================================
# STEP 2
# UPLOAD LOW PRIORITY FILES
# ============================================================

st.header("Step 2 - Upload Low Priority Files")

uploaded_die_files = st.file_uploader(
    "Upload Low Priority Excel Files",
    type=["xlsx"],
    accept_multiple_files=True,
    key="low_priority_files"
)


# ============================================================
# START PROCESSING
# ============================================================

if (
    uploaded_item_files
    and uploaded_die_files
):

    st.divider()

    if st.button(
        "🚀 Process Files",
        type="primary"
    ):

        start = time.time()

        progress_bar = st.progress(0)

        status_text = st.empty()


        # ====================================================
        # INPUT 1 VARIABLES
        # ====================================================

        item_dfs = []

        rows_read = 0

        normal_itemids_to_remove = set()

        mask_row_keys_to_remove = set()

        matched_rows = []


        # ====================================================
        # PROCESS ALL INPUT FILES
        # ====================================================

        status_text.write(
            "### Processing All Input Files..."
        )


        for file_index, uploaded_file in enumerate(
            uploaded_item_files
        ):

            filename = uploaded_file.name


            try:

                df = read_excel_file(
                    uploaded_file
                )

            except Exception as e:

                st.error(str(e))

                continue


            # ================================================
            # REQUIRED COLUMNS
            # ================================================

            required_columns = [

                ITEMID_COLUMN,

                ITEMTYPE_COLUMN,

                PART_COLUMN,

                FIRST_COMPANY_COLUMN

            ]


            missing = [

                col

                for col in required_columns

                if col not in df.columns

            ]


            if missing:

                st.warning(
                    f"{filename} skipped. "
                    f"Missing columns: {missing}"
                )

                continue


            # ================================================
            # ADD ORIGINAL ROW ID
            # ================================================

            df = df.with_row_index(
                "_OriginalRowID"
            )


            # ================================================
            # ADD SOURCE FILE
            # ================================================

            df = df.with_columns(

                pl.lit(filename)
                .alias("SourceFile")

            )


            # ================================================
            # CREATE UNIQUE ROW KEY
            # ================================================

            df = df.with_columns(

                (
                    pl.lit(filename)

                    + "||"

                    + pl.col("_OriginalRowID")
                    .cast(pl.Utf8)
                )

                .alias("_RowKey")

            )


            # ================================================
            # CREATE JOIN COLUMN
            # ================================================

            df = df.with_columns(

                (
                    normalize_column(
                        PART_COLUMN
                    )

                    + "||"

                    + normalize_column(
                        FIRST_COMPANY_COLUMN
                    )
                )

                .alias(
                    FIRST_JOIN_COLUMN
                )

            )


            item_dfs.append(df)

            rows_read += df.height


            # ================================================
            # SEARCH -9999999999
            # ================================================

            available_search_columns = [

                col

                for col in FIRST_SEARCH_COLUMNS

                if col in df.columns

            ]


            if not available_search_columns:

                st.warning(
                    f"{filename}: "
                    f"DistinctValues and ItemName "
                    f"were not found."
                )

                continue


            condition = None


            for col in available_search_columns:

                search_col = (

                    pl.col(col)

                    .cast(
                        pl.Utf8,
                        strict=False
                    )

                    .fill_null("")

                    .str.strip_chars()

                )


                current_condition = (

                    search_col.str.contains(

                        FIRST_SEARCH_VALUE,

                        literal=True

                    )

                )


                if condition is None:

                    condition = current_condition

                else:

                    condition = (

                        condition

                        |

                        current_condition

                    )


            # ================================================
            # GET MATCHED ROWS
            # ================================================

            matched = df.filter(
                condition
            )


            if matched.height > 0:

                matched_rows.append(
                    matched
                )


                # ============================================
                # MASK CONDITION
                # ============================================

                is_mask = (

                    pl.col(ITEMTYPE_COLUMN)

                    .cast(
                        pl.Utf8,
                        strict=False
                    )

                    .fill_null("")

                    .str.strip_chars()

                    .str.to_lowercase()

                    .str.contains(
                        "mask",
                        literal=True
                    )

                )


                # ============================================
                # MASK
                # DELETE ONLY MATCHED ROW
                # ============================================

                mask_matches = matched.filter(
                    is_mask
                )


                if mask_matches.height > 0:

                    mask_keys = (

                        mask_matches

                        .select(
                            "_RowKey"
                        )

                        .to_series()

                        .to_list()

                    )


                    mask_row_keys_to_remove.update(
                        mask_keys
                    )


                # ============================================
                # NON-MASK
                # DELETE ENTIRE ITEM ID
                # ============================================

                non_mask_matches = matched.filter(
                    ~is_mask
                )


                if non_mask_matches.height > 0:

                    ids = (

                        non_mask_matches

                        .select(

                            pl.col(
                                ITEMID_COLUMN
                            )

                            .cast(
                                pl.Utf8,
                                strict=False
                            )

                        )

                        .to_series()

                        .drop_nulls()

                        .to_list()

                    )


                    ids = [

                        str(x).strip()

                        for x in ids

                        if str(x).strip() != ""

                    ]


                    normal_itemids_to_remove.update(
                        ids
                    )


            progress_value = int(

                (
                    file_index + 1
                )

                /

                (
                    len(uploaded_item_files)
                    +
                    len(uploaded_die_files)
                )

                * 50

            )


            progress_bar.progress(
                min(progress_value, 50)
            )


        # ====================================================
        # CHECK ALL INPUT FILES
        # ====================================================

        if len(item_dfs) == 0:

            st.error(
                "No valid All Input files were found."
            )

            st.stop()


        # ====================================================
        # PROCESS LOW PRIORITY FILES
        # ====================================================

        status_text.write(
            "### Processing Low Priority Files..."
        )


        die_dfs = []


        for file_index, uploaded_file in enumerate(
            uploaded_die_files
        ):

            filename = uploaded_file.name


            try:

                df = read_excel_file(
                    uploaded_file
                )

            except Exception as e:

                st.error(str(e))

                continue


            # ================================================
            # REQUIRED COLUMNS
            # ================================================

            required = [

                PART_COLUMN,

                SECOND_COMPANY_COLUMN,

                DIE_FAMILY_COLUMN

            ]


            missing = [

                col

                for col in required

                if col not in df.columns

            ]


            if missing:

                st.warning(
                    f"{filename} skipped. "
                    f"Missing columns: {missing}"
                )

                continue


            # ================================================
            # CREATE JOIN COLUMN
            # ================================================

            df = df.with_columns(

                (

                    normalize_column(
                        PART_COLUMN
                    )

                    + "||"

                    + normalize_column(
                        SECOND_COMPANY_COLUMN
                    )

                )

                .alias(
                    SECOND_JOIN_COLUMN
                )

            )


            # ================================================
            # KEEP REQUIRED COLUMNS
            # ================================================

            df = df.select(

                [

                    SECOND_JOIN_COLUMN,

                    DIE_FAMILY_COLUMN

                ]

            )


            die_dfs.append(df)


            progress_value = int(

                50

                +

                (

                    (file_index + 1)

                    /

                    len(uploaded_die_files)

                    * 25

                )

            )


            progress_bar.progress(
                min(progress_value, 75)
            )


        # ====================================================
        # CHECK LOW PRIORITY FILES
        # ====================================================

        if len(die_dfs) == 0:

            st.error(
                "No valid Low Priority files were found."
            )

            st.stop()


        # ====================================================
        # CONCATENATE LOW PRIORITY FILES
        # ====================================================

        status_text.write(
            "### Creating Low Priority Lookup..."
        )


        die_lookup = pl.concat(

            die_dfs,

            how="diagonal"

        )


        # ====================================================
        # CLEAN DIE FAMILY
        # ====================================================

        die_lookup = die_lookup.with_columns(

            pl.col(
                DIE_FAMILY_COLUMN
            )

            .cast(
                pl.Utf8,
                strict=False
            )

            .fill_null("")

            .str.strip_chars()

            .alias(
                DIE_FAMILY_COLUMN
            )

        )


        # ====================================================
        # REMOVE EMPTY JOIN KEYS
        # ====================================================

        die_lookup = die_lookup.filter(

            pl.col(
                SECOND_JOIN_COLUMN
            )

            != ""

        )


        # ====================================================
        # REMOVE DUPLICATES
        # ====================================================

        die_lookup = die_lookup.unique(

            subset=[
                SECOND_JOIN_COLUMN
            ],

            keep="first"

        )


        # ====================================================
        # PREPARE JOIN
        # ====================================================

        status_text.write(
            "### Matching All Input with Low Priority..."
        )


        die_lookup_for_join = (

            die_lookup

            .rename({

                SECOND_JOIN_COLUMN:
                FIRST_JOIN_COLUMN

            })

        )


        updated_item_dfs = []


        for df in item_dfs:


            # ================================================
            # REMOVE EXISTING DIE FAMILY
            # ================================================

            if DIE_FAMILY_COLUMN in df.columns:

                df = df.drop(
                    DIE_FAMILY_COLUMN
                )


            # ================================================
            # LEFT JOIN
            # ================================================

            df = df.join(

                die_lookup_for_join,

                on=FIRST_JOIN_COLUMN,

                how="left"

            )


            # ================================================
            # CLEAN DIE FAMILY
            # ================================================

            df = df.with_columns(

                pl.col(
                    DIE_FAMILY_COLUMN
                )

                .fill_null("")

                .cast(
                    pl.Utf8,
                    strict=False
                )

                .alias(
                    DIE_FAMILY_COLUMN
                )

            )


            updated_item_dfs.append(df)


        item_dfs = updated_item_dfs


        # ====================================================
        # SEARCH 99999999 IN DIE FAMILY
        # ====================================================

        status_text.write(
            "### Searching 99999999 in DieFamily..."
        )


        die_family_itemids_to_remove = set()

        die_family_matched_rows = []


        for df in item_dfs:

            condition = (

                pl.col(
                    DIE_FAMILY_COLUMN
                )

                .cast(
                    pl.Utf8,
                    strict=False
                )

                .fill_null("")

                .str.strip_chars()

                .str.contains(

                    DIE_FAMILY_SEARCH_VALUE,

                    literal=True

                )

            )


            matched_die_rows = df.filter(
                condition
            )


            if matched_die_rows.height == 0:

                continue


            die_family_matched_rows.append(
                matched_die_rows
            )


            ids = (

                matched_die_rows

                .select(

                    pl.col(
                        ITEMID_COLUMN
                    )

                    .cast(
                        pl.Utf8,
                        strict=False
                    )

                )

                .to_series()

                .drop_nulls()

                .to_list()

            )


            ids = [

                str(x).strip()

                for x in ids

                if x is not None

                and str(x).strip() != ""

            ]


            die_family_itemids_to_remove.update(
                ids
            )


        # ====================================================
        # COMBINE ALL ITEM IDS
        # ====================================================

        all_itemids_to_remove = (

            normal_itemids_to_remove

            |

            die_family_itemids_to_remove

        )


        # ====================================================
        # CREATE ITEM IDS DATAFRAME
        # ====================================================

        itemids_df = (

            pl.DataFrame(

                {

                    ITEMID_COLUMN:
                    list(all_itemids_to_remove)

                }

            )

            .with_columns(

                pl.col(
                    ITEMID_COLUMN
                )

                .cast(
                    pl.Utf8,
                    strict=False
                )

            )

            .unique()

        )


        # ====================================================
        # CREATE MATCHED DATA
        # ====================================================

        all_matched = []


        if len(matched_rows) > 0:

            all_matched.append(

                pl.concat(

                    matched_rows,

                    how="diagonal"

                )

            )


        if len(die_family_matched_rows) > 0:

            all_matched.append(

                pl.concat(

                    die_family_matched_rows,

                    how="diagonal"

                )

            )


        if len(all_matched) > 0:

            matched_df = pl.concat(

                all_matched,

                how="diagonal"

            )

        else:

            matched_df = pl.DataFrame()


        # ====================================================
        # REMOVE DATAFRAME
        # ====================================================

        remove_df = (

            itemids_df

            .select(

                pl.col(
                    ITEMID_COLUMN
                )

                .cast(
                    pl.Utf8,
                    strict=False
                )

                .fill_null("")

                .str.strip_chars()

                .alias(
                    "_ItemIdJoinKey"
                )

            )

            .filter(

                pl.col(
                    "_ItemIdJoinKey"
                )

                != ""

            )

            .unique()

        )


        # ====================================================
        # DELETE FROM ALL INPUT FILES
        # ====================================================

        status_text.write(
            "### Removing matched ItemIds..."
        )


        cleaned = []

        deleted = []

        rows_before = 0

        rows_after = 0

        mask_only_deleted = 0

        whole_item_deleted = 0


        for df in item_dfs:

            rows_before += df.height


            # ================================================
            # CREATE TEMP ITEM ID KEY
            # ================================================

            df = df.with_columns(

                pl.col(
                    ITEMID_COLUMN
                )

                .cast(
                    pl.Utf8,
                    strict=False
                )

                .fill_null("")

                .str.strip_chars()

                .alias(
                    "_ItemIdJoinKey"
                )

            )


            # ================================================
            # DELETE WHOLE ITEM IDS
            # ================================================

            if len(all_itemids_to_remove) > 0:

                whole_deleted = df.join(

                    remove_df,

                    on="_ItemIdJoinKey",

                    how="inner"

                )


                remaining = df.join(

                    remove_df,

                    on="_ItemIdJoinKey",

                    how="anti"

                )

            else:

                whole_deleted = pl.DataFrame(
                    schema=df.schema
                )

                remaining = df


            whole_item_deleted += (
                whole_deleted.height
            )


            # ================================================
            # DELETE MASK ROWS ONLY
            # ================================================

            if len(mask_row_keys_to_remove) > 0:

                mask_keys_df = pl.DataFrame(

                    {

                        "_RowKey":

                        list(
                            mask_row_keys_to_remove
                        )

                    }

                )


                mask_deleted = remaining.join(

                    mask_keys_df,

                    on="_RowKey",

                    how="inner"

                )


                remaining = remaining.join(

                    mask_keys_df,

                    on="_RowKey",

                    how="anti"

                )

            else:

                mask_deleted = pl.DataFrame(
                    schema=remaining.schema
                )


            mask_only_deleted += (
                mask_deleted.height
            )


            # ================================================
            # COMBINE DELETED
            # ================================================

            deleted_rows = pl.concat(

                [

                    whole_deleted,

                    mask_deleted

                ],

                how="diagonal"

            )


            # ================================================
            # REMOVE TEMP KEY
            # ================================================

            remaining = remaining.drop(

                "_ItemIdJoinKey",

                strict=False

            )


            deleted_rows = deleted_rows.drop(

                "_ItemIdJoinKey",

                strict=False

            )


            cleaned.append(
                remaining
            )


            deleted.append(
                deleted_rows
            )


            rows_after += remaining.height


        # ====================================================
        # MERGE CLEANED FILES
        # ====================================================

        status_text.write(
            "### Preparing final output..."
        )


        final_df = pl.concat(

            cleaned,

            how="diagonal"

        )


        # ====================================================
        # MERGE DELETED FILES
        # ====================================================

        if len(deleted) > 0:

            deleted_df = pl.concat(

                deleted,

                how="diagonal"

            )

        else:

            deleted_df = pl.DataFrame()


        # ====================================================
        # REMOVE HELPER COLUMNS
        # ====================================================

        helper_columns = [

            "_OriginalRowID",

            "_RowKey"

        ]


        for col in helper_columns:

            if col in final_df.columns:

                final_df = final_df.drop(
                    col
                )


            if col in deleted_df.columns:

                deleted_df = deleted_df.drop(
                    col
                )


        # ====================================================
        # CREATE OUTPUT FILES IN MEMORY
        # ====================================================

        status_text.write(
            "### Creating output files..."
        )


        generated_files = []


        # ====================================================
        # DELETED ROWS
        # ====================================================

        deleted_buffer = io.BytesIO()

        deleted_df.write_excel(
            deleted_buffer
        )

        generated_files.append(

            (

                "Deleted_ItemIds_Rows.xlsx",

                deleted_buffer.getvalue()

            )

        )


        # ====================================================
        # MATCHED ROWS
        # ====================================================

        if matched_df.height > 0:

            matched_output_df = matched_df.drop(

                [

                    "_OriginalRowID",

                    "_RowKey"

                ],

                strict=False

            )

        else:

            matched_output_df = pl.DataFrame()


        matched_buffer = io.BytesIO()

        matched_output_df.write_excel(
            matched_buffer
        )

        generated_files.append(

            (

                "Matched_Rows.xlsx",

                matched_buffer.getvalue()

            )

        )


        # ====================================================
        # ITEM IDS
        # ====================================================

        itemids_buffer = io.BytesIO()

        itemids_df.write_excel(
            itemids_buffer
        )

        generated_files.append(

            (

                "ItemIds_To_Delete.xlsx",

                itemids_buffer.getvalue()

            )

        )


        # ====================================================
        # SAVE FINAL OUTPUT
        # ====================================================

        total_rows = final_df.height


        if total_rows <= MAX_ROWS_PER_FILE:

            output_buffer = io.BytesIO()

            final_df.write_excel(
                output_buffer
            )

            generated_files.append(

                (

                    "Merged_Cleaned_Output.xlsx",

                    output_buffer.getvalue()

                )

            )


        else:

            part = 1


            for start_row in range(

                0,

                total_rows,

                MAX_ROWS_PER_FILE

            ):

                chunk_size = min(

                    MAX_ROWS_PER_FILE,

                    total_rows - start_row

                )


                chunk = final_df.slice(

                    start_row,

                    chunk_size

                )


                output_buffer = io.BytesIO()


                chunk.write_excel(
                    output_buffer
                )


                output_name = (

                    f"Merged_Cleaned_Output_"
                    f"Part_{part}.xlsx"

                )


                generated_files.append(

                    (

                        output_name,

                        output_buffer.getvalue()

                    )

                )


                part += 1


        # ====================================================
        # CREATE ZIP IN MEMORY
        # ====================================================

        status_text.write(
            "### Creating ZIP file..."
        )


        zip_buffer = io.BytesIO()


        with zipfile.ZipFile(

            zip_buffer,

            "w",

            zipfile.ZIP_DEFLATED

        ) as z:

            for filename, file_data in generated_files:

                z.writestr(

                    filename,

                    file_data

                )


        zip_buffer.seek(0)


        # ====================================================
        # FINISHED
        # ====================================================

        progress_bar.progress(100)

        status_text.empty()


        elapsed = time.time() - start


        st.success(
            "🎉 Finished Successfully!"
        )


        # ====================================================
        # SUMMARY
        # ====================================================

        st.subheader(
            "Processing Summary"
        )


        col1, col2, col3 = st.columns(3)


        col1.metric(
            "Input Files",
            len(item_dfs)
        )


        col2.metric(
            "Rows Read",
            f"{rows_read:,}"
        )


        col3.metric(
            "Remaining Rows",
            f"{final_df.height:,}"
        )


        col1.metric(
            "Normal ItemIds",
            f"{len(normal_itemids_to_remove):,}"
        )


        col2.metric(
            "DieFamily ItemIds",
            f"{len(die_family_itemids_to_remove):,}"
        )


        col3.metric(
            "Total ItemIds Deleted",
            f"{len(all_itemids_to_remove):,}"
        )


        col1.metric(
            "Mask Rows Deleted",
            f"{mask_only_deleted:,}"
        )


        col2.metric(
            "Total Rows Deleted",
            f"{rows_before - rows_after:,}"
        )


        col3.metric(
            "Execution Time",
            f"{elapsed:.2f} sec"
        )


        # ====================================================
        # GENERATED FILES
        # ====================================================

        st.subheader(
            "Generated Files"
        )


        for filename, _ in generated_files:

            st.write(
                f"📄 {filename}"
            )


        # ====================================================
        # DOWNLOAD ZIP
        # ====================================================

        st.download_button(

            label="📦 Download All Results (ZIP)",

            data=zip_buffer.getvalue(),

            file_name="Results.zip",

            mime="application/zip",

            type="primary"

        )


else:

    st.info(
        "Please upload both All Input files "
        "and Low Priority files to start processing."
    )


# ============================================================
# FOOTER
# ============================================================

st.markdown("---")

st.caption(
    "Collect & 9999 Processor | Streamlit"
)
```
