node('master_pipeline') {
   stage 'Parse build job info'
   def job_name = "${BUILD_JOB_NAME}"
   def build_number = "${BUILD_JOB_NUMBER}"
   def job_name_arr = job_name.tokenize('-')
   def branch_name  = job_name_arr[1]
   def machine_name = job_name_arr[3]
   git branch: 'dev', url: 'http://mod.lge.com/hub/tv_scm_tool/compare_foss_diff.git'

   stage 'Check foss change'
   sh "python compare_foss_diff.py --jobname ${BUILD_JOB_NAME} --buildnumber ${BUILD_JOB_NUMBER} > compare_result"
    sh 'ls -al'
   sh "cat compare_result"
   def compare_result = readFile 'compare_result'
   echo "test-previous"
   echo compare_result.toString()
   echo "test"
   if ( compare_result == "CHANGED\n" ) {
       stage 'Call a clean engineering build'
       //clean-engineering-starfish-m16-build
       echo 'Clean Build'
       def clean_job_name = "clean-engineering-starfish-" + machine_name + "-build"
    /*
       join = parallel([clean: {
            node('verification'){
                build job:clean_job_name, parameters: [
                    [$class: 'StringParameterValue',  name:'build_codename',        value:branch_name],
                    [$class: 'StringParameterValue',  name:'token',                 value:'trigger_clean_build'],
                    [$class: 'StringParameterValue',  name:'extra_images',          value:'starfish-bdk'],
                    [$class: 'StringParameterValue',  name:'build_starfish_commit', value:'@drd4tv'],
                    [$class: 'TextParameterValue',    name:'webos_local',           value:'WEBOS_DISTRO_BUILD_ID="318"\nSDKMACHINE="i686"'],
                    [$class: 'StringParameterValue',  name:'Build_summary',         value:'test bdk build'],
                    [$class: 'BooleanParameterValue', name:'Build_starfish_m16p',   value:true],
                    [$class: 'BooleanParameterValue', name:'region_default',        value:false],
                    [$class: 'BooleanParameterValue', name:'region_atsc',           value:false],
                    [$class: 'BooleanParameterValue', name:'region_arib',           value:false],
                    [$class: 'BooleanParameterValue', name:'region_dvb',            value:false],
                ]
            }
        }
        ])


        def clean_build_result = join.clean.result
        def clean_build_number = join.clean.number.toString()
        */
        def clean_build_result = "${CLEAN_BUILD_RESULT}"
        def clean_build_number = "${CLEAN_BUILD_NUMBER}"
        stage 'Copy bdk result'
        node('verification'){
            def bdk_job_name = "starfish-bdk"
            def org_dir = '/binary/build_results/starfish_verifications/' + clean_job_name + '/' + clean_build_number
            def target_root = '/binary/build_results/temp/' + bdk_job_name
            def target_dir = target_root + '/' + "${env.BUILD_NUMBER}"+ "_bdk"

            sh 'mkdir -p ' + target_root
            sh 'cp -r ' + org_dir + '/ ' + target_dir
        }
    }
}
